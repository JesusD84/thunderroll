import os
from functools import lru_cache

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

# A syntactically valid fallback sender so the config can always be built, even
# with no SMTP envs (e.g. when running tests). Real delivery still requires
# SMTP_USER/SMTP_FROM to be set to a real address.
_DEFAULT_MAIL_FROM = "noreply@example.com"


def _frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:3000")


@lru_cache(maxsize=1)
def get_mail_config() -> ConnectionConfig:
    """Build the FastMail connection config lazily.

    Reading the environment and validating ``MAIL_FROM`` happen on first use
    (when an email is actually sent), not at import time. This keeps importing
    the app and running the test suite from requiring SMTP envs, while real
    delivery still works once they are configured. See TR-10.
    """
    smtp_user = os.getenv("SMTP_USER", "")
    return ConnectionConfig(
        MAIL_USERNAME=smtp_user,
        MAIL_PASSWORD=os.getenv("SMTP_PASSWORD", ""),
        MAIL_FROM=os.getenv("SMTP_FROM") or smtp_user or _DEFAULT_MAIL_FROM,
        MAIL_PORT=int(os.getenv("SMTP_PORT", "587")),
        MAIL_SERVER=os.getenv("SMTP_HOST", "smtp.gmail.com"),
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
    )


async def send_password_reset_email(to_email: str, reset_token: str) -> None:
    reset_url = f"{_frontend_url()}/reset-password?token={reset_token}"

    html_body = f"""
    <p>You requested a password reset for your Thunderrol account.</p>
    <p>Click the link below to reset your password. This link expires in 15 minutes.</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>If you did not request this, you can safely ignore this email.</p>
    """

    plain_body = (
        f"You requested a password reset for your Thunderrol account.\n\n"
        f"Click the link below to reset your password (expires in 15 minutes):\n"
        f"{reset_url}\n\n"
        f"If you did not request this, you can safely ignore this email."
    )

    message = MessageSchema(
        subject="Thunderrol — Password Reset Request",
        recipients=[to_email],
        body=html_body,
        subtype=MessageType.html,
        alternative_body=plain_body,
    )

    fm = FastMail(get_mail_config())
    await fm.send_message(message)
