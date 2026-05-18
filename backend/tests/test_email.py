"""Unit tests for email service."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@patch("app.services.email.FastMail")
async def test_send_password_reset_email(mock_fastmail_cls):
    """Constructs and sends a password reset email."""
    mock_fm = AsyncMock()
    mock_fastmail_cls.return_value = mock_fm

    from app.services.email import send_password_reset_email

    await send_password_reset_email("user@example.com", "abc123token")

    mock_fastmail_cls.assert_called_once()
    mock_fm.send_message.assert_awaited_once()

    call_args = mock_fm.send_message.call_args[0][0]
    assert call_args.recipients == ["user@example.com"]
    assert "abc123token" in call_args.body
    assert "Thunderrol" in call_args.subject


@patch("app.services.email.FastMail")
@patch("app.services.email.MessageSchema")
async def test_send_password_reset_email_uses_frontend_url(mock_msg_schema, mock_fastmail_cls):
    """Reset URL includes the frontend base URL."""
    mock_fm = AsyncMock()
    mock_fastmail_cls.return_value = mock_fm
    mock_msg = MagicMock()
    mock_msg_schema.return_value = mock_msg

    from app.services.email import send_password_reset_email

    await send_password_reset_email("test@test.com", "tok123")

    call_kwargs = mock_msg_schema.call_args[1]
    assert "reset-password?token=tok123" in call_kwargs["body"]
    assert "reset-password?token=tok123" in call_kwargs["alternative_body"]


@patch("app.services.email.FastMail")
@patch("app.services.email.MessageSchema")
async def test_send_password_reset_email_plain_text_alternative(mock_msg_schema, mock_fastmail_cls):
    """Email includes a plain text alternative body."""
    mock_fm = AsyncMock()
    mock_fastmail_cls.return_value = mock_fm
    mock_msg = MagicMock()
    mock_msg_schema.return_value = mock_msg

    from app.services.email import send_password_reset_email

    await send_password_reset_email("a@b.com", "xyz")

    call_kwargs = mock_msg_schema.call_args[1]
    assert call_kwargs["alternative_body"] is not None
    assert "xyz" in call_kwargs["alternative_body"]
