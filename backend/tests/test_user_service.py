"""Unit tests for UserService."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.services.user_service import UserService
from app.models.models import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


# ---------------------------------------------------------------------------
# register_user
# ---------------------------------------------------------------------------

@patch("app.services.user_service.UserRepository")
@patch("app.services.user_service.get_password_hash")
def test_register_user_success(mock_hash, mock_repo):
    """Registers a new user when email and username are unique."""
    mock_db = MagicMock()
    user_data = UserCreate(
        email="new@test.com",
        username="newuser",
        first_name="New",
        last_name="User",
        role=UserRole.VIEWER,
        password="password123",
    )

    mock_repo.get_user_by_email.return_value = None
    mock_repo.get_user_by_username.return_value = None
    mock_hash.return_value = "hashed_abc"
    mock_user = User(id=2, username="newuser", email="new@test.com")
    mock_repo.create_user.return_value = mock_user

    result = UserService.register_user(mock_db, user_data)

    mock_repo.get_user_by_email.assert_called_once_with(mock_db, email="new@test.com")
    mock_repo.get_user_by_username.assert_called_once_with(mock_db, username="newuser")
    mock_hash.assert_called_once_with("password123")
    mock_repo.create_user.assert_called_once_with(mock_db, user_data, "hashed_abc")
    assert result is mock_user


@patch("app.services.user_service.UserRepository")
def test_register_user_duplicate_email(mock_repo):
    """Raises 400 when email is already registered."""
    mock_db = MagicMock()
    user_data = UserCreate(
        email="existing@test.com",
        username="newuser",
        first_name="New",
        last_name="User",
        role=UserRole.VIEWER,
        password="password123",
    )

    mock_repo.get_user_by_email.return_value = User(id=1, email="existing@test.com")

    with pytest.raises(HTTPException) as exc:
        UserService.register_user(mock_db, user_data)
    assert exc.value.status_code == 400
    assert "Email already registered" in exc.value.detail


@patch("app.services.user_service.UserRepository")
def test_register_user_duplicate_username(mock_repo):
    """Raises 400 when username is already taken."""
    mock_db = MagicMock()
    user_data = UserCreate(
        email="new@test.com",
        username="existinguser",
        first_name="New",
        last_name="User",
        role=UserRole.VIEWER,
        password="password123",
    )

    mock_repo.get_user_by_email.return_value = None
    mock_repo.get_user_by_username.return_value = User(id=1, username="existinguser")

    with pytest.raises(HTTPException) as exc:
        UserService.register_user(mock_db, user_data)
    assert exc.value.status_code == 400
    assert "Username already registered" in exc.value.detail


# ---------------------------------------------------------------------------
# update_current_user
# ---------------------------------------------------------------------------

@patch("app.services.user_service.UserRepository")
def test_update_current_user_success(mock_repo):
    """Delegates to UserRepository.update_user."""
    mock_db = MagicMock()
    current_user = User(id=1, username="admin", email="admin@test.com")
    user_update = UserUpdate(first_name="Updated")
    mock_repo.update_user.return_value = current_user

    result = UserService.update_current_user(mock_db, current_user, user_update)

    mock_repo.update_user.assert_called_once_with(mock_db, current_user, user_update)
    assert result is current_user
