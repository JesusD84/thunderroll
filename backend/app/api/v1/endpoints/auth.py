import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.rate_limit import (
    FORGOT_PASSWORD_LIMIT_PER_MINUTE,
    LOGIN_LIMIT_PER_MINUTE,
    REFRESH_LIMIT_PER_MINUTE,
    account_key,
    ip_key,
    limiter,
    refresh_account_key,
)
from app.database.database import get_db
from app.models import schemas
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_SECONDS,
    authenticate_user,
    create_access_token,
    create_password_reset_token,
    create_refresh_token,
    get_password_hash,
    get_user_by_email,
    get_user_by_id,
    refresh_oauth2_scheme,
    verify_password_against_dummy,
    verify_password_reset_token,
    verify_refresh_token,
)
from app.services.email import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter()


async def _send_reset_email_background(to_email: str, reset_token: str) -> None:
    """Envía el correo de reset fuera del ciclo de la petición.

    El correo se manda en segundo plano a propósito: si el SMTP está lento (o
    caído), el endpoint no puede tardar más que con un correo desconocido. Y
    como el envío no decide el status de la respuesta, un fallo de SMTP ya no
    puede revelar si la cuenta existe: solo queda en el log.
    """
    try:
        await send_password_reset_email(to_email=to_email, reset_token=reset_token)
    except Exception:
        # Un SMTP roto tiene que ser visible, pero no puede romper la
        # respuesta: el log es el lugar donde se ve.
        logger.exception("Failed to send password reset email to %s", to_email)


@router.post("/login", response_model=schemas.Token)
@limiter.limit(lambda key: f"{LOGIN_LIMIT_PER_MINUTE}/minute", key_func=ip_key)
@limiter.limit(lambda key: f"{LOGIN_LIMIT_PER_MINUTE}/minute", key_func=account_key)
async def login_for_access_token(
    request: Request,
    # El limitador escribe aquí las cabeceras X-RateLimit-*. FastAPI las
    # mezcla con la respuesta final: sin este parámetro, slowapi no tiene
    # dónde ponerlas.
    response: Response,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # El token lleva el id del usuario (no el username), el tipo "access" y la
    # versión del token del usuario: si después se cambia la contraseña, el rol
    # o se da de baja la cuenta, este token deja de servir.
    access_token = create_access_token(user)
    # El token de refresco permite pedir un access token nuevo cuando este ya
    # venció, sin volver a pedir la contraseña.
    refresh_token = create_refresh_token(user)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
    }


@router.post("/refresh", response_model=schemas.Token)
@limiter.limit(lambda key: f"{REFRESH_LIMIT_PER_MINUTE}/minute", key_func=ip_key)
@limiter.limit(
    lambda key: f"{REFRESH_LIMIT_PER_MINUTE}/minute", key_func=refresh_account_key
)
async def refresh_access_token(
    request: Request,
    # Véase el comentario del login: aquí el limitador también escribe las
    # cabeceras X-RateLimit-*.
    response: Response,
    credentials: str | None = Depends(refresh_oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Emite un token de acceso nuevo a partir de un token de refresco.

    Es lo que permite que la sesión sobreviva a la caducidad del token de
    acceso: el frontend lo llama cuando el backend le responde 401.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = verify_refresh_token(credentials)

    user = get_user_by_id(db, user_id=claims.user_id)
    if user is None or user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # La versión tiene que coincidir: si las credenciales cambiaron, el token
    # de refresco también queda revocado y la sesión se cierra.
    if (user.token_version or 0) != claims.token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(user),
        # El token de refresco no rota: el frontend guarda el que ya tiene.
        "refresh_token": credentials,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_SECONDS,
    }


@router.post("/forgot-password")
@limiter.limit(
    lambda key: f"{FORGOT_PASSWORD_LIMIT_PER_MINUTE}/minute", key_func=ip_key
)
@limiter.limit(
    lambda key: f"{FORGOT_PASSWORD_LIMIT_PER_MINUTE}/minute", key_func=account_key
)
async def forgot_password(
    request: Request,
    # Véase el comentario del login: aquí el limitador también escribe las
    # cabeceras X-RateLimit-*.
    response: Response,
    background_tasks: BackgroundTasks,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, email=payload.email)
    if user:
        reset_token = create_password_reset_token(user.email, user.token_version or 0)
        background_tasks.add_task(_send_reset_email_background, user.email, reset_token)
    else:
        # Correo desconocido: se ejecuta igualmente un bcrypt para que el
        # tiempo de respuesta sea el mismo que con una cuenta real.
        verify_password_against_dummy(payload.email)
    # A non-existent email still answers 200: the response must not reveal
    # whether an account exists.
    return {"message": "If that email exists, a reset link was sent."}


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    claims = verify_password_reset_token(request.token)
    user = get_user_by_email(db, email=claims.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )
    # El token queda atado a la versión del usuario: si la versión ya no
    # coincide, el token se usó antes (cambiar la contraseña sube la versión)
    # o quedó revocado por otro cambio de credenciales.
    if (user.token_version or 0) != claims.token_version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )
    user.hashed_password = get_password_hash(request.new_password)
    # Subir la versión deja el token sin uso: un segundo canje del mismo token
    # ya no encuentra la versión que espera y se rechaza.
    user.token_version = (user.token_version or 0) + 1
    db.commit()
    return {"message": "Password updated successfully."}
