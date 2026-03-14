import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

_mail_config = ConnectionConfig(
    MAIL_USERNAME=SMTP_USER,
    MAIL_PASSWORD=SMTP_PASSWORD,
    MAIL_FROM=SMTP_FROM,
    MAIL_PORT=SMTP_PORT,
    MAIL_SERVER=SMTP_HOST,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

async def send_password_reset_email(to_email: str, reset_token: str) -> None:
    reset_url = f"{FRONTEND_URL}/reset-password?token={reset_token}"

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

    fm = FastMail(_mail_config)
    await fm.send_message(message)
