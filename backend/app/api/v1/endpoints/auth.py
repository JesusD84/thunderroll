
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import schemas
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    create_password_reset_token,
    get_password_hash,
    get_user_by_email,
    verify_password_reset_token,
)
from app.services.email import send_password_reset_email

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    user = get_user_by_email(db, email=request.email)
    if user:
        try:
            reset_token = create_password_reset_token(user.email)
            await send_password_reset_email(to_email=user.email, reset_token=reset_token)
        except Exception as exc:
            logger.exception("Failed to send password reset email to %s", user.email)
            # A broken SMTP must be visible. Answering 200 here would be
            # indistinguishable from a successful send, and this endpoint is
            # the only self-service way back into an account: a silent failure
            # would leave the user locked out with no clue why.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not send the reset email. Try again later.",
            ) from exc
    # A non-existent email still answers 200: the response must not reveal
    # whether an account exists.
    return {"message": "If that email exists, a reset link was sent."}

@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    email = verify_password_reset_token(request.token)
    user = get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset token",
        )
    user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    return {"message": "Password updated successfully."}
