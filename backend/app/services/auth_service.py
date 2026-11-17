import os
from datetime import UTC, datetime, timedelta
from typing import NamedTuple

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import require_secret_key
from app.core.security import Security
from app.database.database import get_db
from app.models.models import User
from app.models.schemas import TokenData

# La clave de firma de los JWT viene solo del entorno. Si falta o es corta,
# `require_secret_key` lanza ConfigurationError y la app no arranca: una clave
# fija en el código (o una clave corta) dejaría firmar tokens a cualquiera que
# lea el repositorio.
SECRET_KEY = require_secret_key()
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
ACCESS_TOKEN_EXPIRE_SECONDS = ACCESS_TOKEN_EXPIRE_MINUTES * 60
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES = 15
# El token de refresco vive mucho más que el de acceso: es el que permite
# renovar la sesión sin volver a pedir la contraseña. También está atado a la
# versión del token del usuario, así que un cambio de credenciales lo invalida
# igual que a los tokens de acceso.
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Tipo de token. Cada token dice qué es, y cada punto de uso exige el tipo
# que espera: un token de reset no sirve como credencial de API y un token de
# acceso no sirve para resetear la contraseña.
TOKEN_TYPE_ACCESS = "access"
TOKEN_TYPE_PASSWORD_RESET = "password_reset"
TOKEN_TYPE_REFRESH = "refresh"

# Claim que lleva la versión del token del usuario. Si el valor guardado en la
# base ya no coincide con el del token, el token está revocado.
TOKEN_VERSION_CLAIM = "ver"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")
# El esquema del refresco no falla por sí solo cuando falta la cabecera: el
# endpoint responde con su propio 401, que dice más que el error genérico.
refresh_oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/auth/login", auto_error=False
)

# Hash bcrypt de una contraseña que no corresponde a ninguna cuenta. Se usa
# para igualar el tiempo de respuesta cuando el usuario no existe: si el
# login respondiera más rápido para un usuario inexistente, el tiempo de
# respuesta revelaría qué correos tienen cuenta.
DUMMY_PASSWORD_HASH = "$2b$12$noXMr3zv/j5gnfEgXX6w2uF4mQC1eJ7GNt1jTsQ.cZvv3caAduyVC"


class ResetTokenClaims(NamedTuple):
    """Lo que un token de reset de contraseña lleva dentro."""

    email: str
    token_version: int


class RefreshTokenClaims(NamedTuple):
    """Lo que un token de refresco lleva dentro."""

    user_id: int
    token_version: int


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def verify_password_against_dummy(plain_password: str) -> None:
    """Verifica la contraseña contra un hash que no corresponde a nadie.

    Existe para que el tiempo de respuesta del login y del forgot-password no
    dependa de si la cuenta existe: las dos rutas ejecutan siempre un bcrypt.
    El resultado se descarta; solo importa el costo.
    """
    try:
        pwd_context.verify(plain_password, DUMMY_PASSWORD_HASH)
    except Exception:
        # Un hash malformado no debe tumbar el endpoint: el objetivo es
        # únicamente gastar el mismo tiempo, no validar nada.
        pass


def get_password_hash(password):
    return Security.get_password_hash(password)


def create_access_token(user: User, expires_delta: timedelta | None = None):
    """Firma un token de acceso para el usuario indicado.

    Los claims los arma esta función y no el llamador, para que ningún token
    pueda salir sin ``typ`` ni sin la versión: un token de acceso sin versión
    no se podría revocar y uno sin tipo se podría usar como token de reset.

    - ``sub``: el id del usuario (no el username). El id no cambia y no se
      puede reutilizar por otro cuenta.
    - ``typ``: ``access``. Distingue este token de un token de reset.
    - ``ver``: la versión del token del usuario. Si el usuario cambia su
      contraseña, su rol o se desactiva, la versión se incrementa y este token
      deja de ser válido.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": str(user.id),
        "typ": TOKEN_TYPE_ACCESS,
        TOKEN_VERSION_CLAIM: user.token_version or 0,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        user = get_user_by_email(db, username)
    if not user:
        # El usuario no existe: se ejecuta igualmente un bcrypt contra un hash
        # ficticio para que el tiempo de respuesta sea el mismo que con una
        # cuenta real.
        verify_password_against_dummy(password)
        return False
    # A deactivated account must not authenticate at all: handing out a token
    # would keep the credentials alive even though every business endpoint
    # rejects the user right after. Only an explicit False deactivates:
    # the column is nullable, so NULL means "not set", not "disabled".
    if user.is_active is False:
        verify_password_against_dummy(password)
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """Resuelve el usuario que dice el token, o falla con 401.

    Se comprueban tres cosas, en este orden:

    1. que el token sea de tipo ``access`` (un token de reset no abre sesión);
    2. que el ``sub`` sea el id de un usuario que existe;
    3. que la versión del token coincida con la del usuario (si no, el token
       fue revocado por un cambio de contraseña o por una baja).
    """
    credentials_exception = _credentials_exception()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc

    if payload.get("typ") != TOKEN_TYPE_ACCESS:
        raise credentials_exception

    raw_sub = payload.get("sub")
    try:
        user_id = int(raw_sub)
    except (TypeError, ValueError) as exc:
        raise credentials_exception from exc

    token_data = TokenData(user_id=user_id)

    user = get_user_by_id(db, user_id=token_data.user_id)
    if user is None:
        raise credentials_exception

    token_version = payload.get(TOKEN_VERSION_CLAIM)
    if token_version != (user.token_version or 0):
        # El token es anterior a un cambio de credenciales: está revocado.
        raise credentials_exception

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.is_active is False:
        # 401 (not 400): the frontend only runs the sign-out flow on 401, so a
        # 400 would leave the user staring at a generic error instead of being
        # redirected to the login page.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def require_role(required_roles: list):
    def role_checker(current_user: User = Depends(get_current_active_user)):
        if current_user.role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
            )
        return current_user

    # Introspection hook: the authorization-matrix test reads the roles a
    # route requires from here, instead of hardcoding them in the test.
    role_checker.required_roles = tuple(required_roles)
    return role_checker


def create_refresh_token(user: User) -> str:
    """Firma el token de refresco de la sesión de un usuario.

    Es el token que permite pedir un access token nuevo cuando el primero ya
    venció, sin volver a pedir la contraseña. Como el de acceso, lleva la
    versión del usuario: si cambian las credenciales, este token deja de
    servir y la sesión se cierra de verdad.
    """
    expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": str(user.id),
        "typ": TOKEN_TYPE_REFRESH,
        TOKEN_VERSION_CLAIM: user.token_version or 0,
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_refresh_token(token: str) -> RefreshTokenClaims:
    """Valida un token de refresco y devuelve a qué cuenta pertenece.

    Solo acepta tokens de tipo ``refresh``: un token de acceso no sirve para
    renovar la sesión, y un token de reset tampoco.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise unauthorized from exc

    if payload.get("typ") != TOKEN_TYPE_REFRESH:
        raise unauthorized

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError) as exc:
        raise unauthorized from exc

    try:
        token_version = int(payload.get(TOKEN_VERSION_CLAIM, 0))
    except (TypeError, ValueError) as exc:
        raise unauthorized from exc

    return RefreshTokenClaims(user_id=user_id, token_version=token_version)


def create_password_reset_token(email: str, token_version: int) -> str:
    """Firma un token de reset de contraseña de un solo uso.

    El token queda atado a la versión del token del usuario. Canjearlo cambia
    la contraseña, y eso incrementa la versión: el token deja de coincidir con
    la versión guardada y no se puede usar por segunda vez. Tampoco sirve un
    token emitido antes de un cambio de credenciales.
    """
    expire = datetime.now(UTC) + timedelta(minutes=PASSWORD_RESET_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": email,
        "typ": TOKEN_TYPE_PASSWORD_RESET,
        TOKEN_VERSION_CLAIM: token_version or 0,
        "exp": expire,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_password_reset_token(token: str) -> ResetTokenClaims:
    """Valida un token de reset y devuelve a quién pertenece.

    Solo acepta tokens de tipo ``password_reset``: un token de acceso (o un
    token sin tipo) se rechaza, porque cada tipo solo vale para lo suyo.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        ) from exc

    if payload.get("typ") != TOKEN_TYPE_PASSWORD_RESET:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token type",
        )

    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )

    raw_version = payload.get(TOKEN_VERSION_CLAIM, 0)
    try:
        token_version = int(raw_version)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        ) from exc

    return ResetTokenClaims(email=email, token_version=token_version)
