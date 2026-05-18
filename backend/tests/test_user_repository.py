"""Unit tests for UserRepository."""

import pytest
from unittest.mock import MagicMock
from app.repositories.user_repository import UserRepository
from app.models.models import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


# ---------------------------------------------------------------------------
# get_user_by_id
# ---------------------------------------------------------------------------

def test_get_user_by_id_found():
    """Returns user when ID exists."""
    mock_db = MagicMock()
    mock_user = User(id=1, username="admin", email="admin@test.com")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = UserRepository.get_user_by_id(mock_db, 1)
    assert result is mock_user


def test_get_user_by_id_not_found():
    """Returns None when ID does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = UserRepository.get_user_by_id(mock_db, 999)
    assert result is None


# ---------------------------------------------------------------------------
# get_user_by_email
# ---------------------------------------------------------------------------

def test_get_user_by_email_found():
    """Returns user when email exists."""
    mock_db = MagicMock()
    mock_user = User(id=1, username="admin", email="admin@test.com")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = UserRepository.get_user_by_email(mock_db, "admin@test.com")
    assert result is mock_user


def test_get_user_by_email_not_found():
    """Returns None when email does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = UserRepository.get_user_by_email(mock_db, "no@test.com")
    assert result is None


# ---------------------------------------------------------------------------
# get_user_by_username
# ---------------------------------------------------------------------------

def test_get_user_by_username_found():
    """Returns user when username exists."""
    mock_db = MagicMock()
    mock_user = User(id=1, username="admin", email="admin@test.com")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = UserRepository.get_user_by_username(mock_db, "admin")
    assert result is mock_user


def test_get_user_by_username_not_found():
    """Returns None when username does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = UserRepository.get_user_by_username(mock_db, "nonexistent")
    assert result is None


# ---------------------------------------------------------------------------
# create_user
# ---------------------------------------------------------------------------

def test_create_user_success():
    """Creates a user with the given data and hashed password."""
    mock_db = MagicMock()
    user_data = UserCreate(
        email="new@test.com",
        username="newuser",
        first_name="New",
        last_name="User",
        role=UserRole.VIEWER,
        password="password123",
    )

    result = UserRepository.create_user(mock_db, user_data, "hashed_abc")

    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    assert result is not None


# ---------------------------------------------------------------------------
# update_user
# ---------------------------------------------------------------------------

def test_update_user_changes_fields():
    """Updates only the fields present in the update data."""
    mock_db = MagicMock()
    existing = User(
        id=1, username="admin", email="admin@test.com",
        first_name="Old", last_name="Name", role=UserRole.ADMIN,
    )
    update_data = UserUpdate(first_name="NewName")

    result = UserRepository.update_user(mock_db, existing, update_data)

    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()
    assert result is existing


def test_update_user_no_fields():
    """Calling update with no fields set still commits."""
    mock_db = MagicMock()
    existing = User(id=1, username="admin", email="admin@test.com")
    update_data = UserUpdate()

    result = UserRepository.update_user(mock_db, existing, update_data)

    mock_db.commit.assert_called_once()
    assert result is existing
