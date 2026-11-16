"""Unit tests for auth service functions."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from jose import jwt

from app.models.models import User, UserRole
from app.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_PASSWORD_RESET,
    authenticate_user,
    create_access_token,
    create_password_reset_token,
    get_current_active_user,
    get_password_hash,
    get_user_by_email,
    get_user_by_username,
    require_role,
    verify_password,
    verify_password_reset_token,
)

# ---------------------------------------------------------------------------
# verify_password
# ---------------------------------------------------------------------------


def test_verify_password_correct():
    """verify_password returns True for correct password."""
    from passlib.context import CryptContext

    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_incorrect():
    """verify_password returns False for wrong password."""
    from passlib.context import CryptContext

    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash("mypassword")
    assert verify_password("wrongpassword", hashed) is False


# ---------------------------------------------------------------------------
# get_password_hash
# ---------------------------------------------------------------------------


def test_get_password_hash_returns_different_string():
    """get_password_hash returns a string different from the input."""
    result = get_password_hash("mypassword")
    assert isinstance(result, str)
    assert result != "mypassword"


def test_get_password_hash_is_verifiable():
    """Hash produced by get_password_hash can be verified."""
    hashed = get_password_hash("mypassword")
    assert verify_password("mypassword", hashed) is True


# ---------------------------------------------------------------------------
# create_access_token
# ---------------------------------------------------------------------------


def test_create_access_token_contains_sub():
    """Token encodes the 'sub' claim with the user id (not the username)."""
    user = User(id=7, username="admin", email="admin@test.com", token_version=0)
    token = create_access_token(user)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "7"


def test_create_access_token_contains_type():
    """The token declares its own type, so it cannot be used as a reset token."""
    user = User(id=7, username="admin", email="admin@test.com", token_version=0)
    token = create_access_token(user)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["typ"] == TOKEN_TYPE_ACCESS


def test_create_access_token_contains_token_version():
    """The token carries the revocation counter of the account."""
    user = User(id=7, username="admin", email="admin@test.com", token_version=3)
    token = create_access_token(user)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["ver"] == 3


def test_create_access_token_contains_exp():
    """Token contains an expiration claim."""
    user = User(id=7, username="admin", email="admin@test.com", token_version=0)
    token = create_access_token(user)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert "exp" in payload


def test_create_access_token_default_expiry():
    """Default expiry is ACCESS_TOKEN_EXPIRE_MINUTES from now."""
    before = datetime.now(UTC)
    user = User(id=7, username="admin", email="admin@test.com", token_version=0)
    token = create_access_token(user)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    after = datetime.now(UTC)
    expected_min = before + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expected_max = (
        after + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES) + timedelta(seconds=5)
    )
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    assert expected_min - timedelta(seconds=5) <= exp <= expected_max


def test_create_access_token_custom_expiry():
    """Custom expires_delta is respected."""
    delta = timedelta(minutes=5)
    user = User(id=7, username="admin", email="admin@test.com", token_version=0)
    token = create_access_token(user, expires_delta=delta)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    now = datetime.now(UTC)
    assert (exp - now).total_seconds() <= 310  # 5 min + small margin


# ---------------------------------------------------------------------------
# get_user_by_username
# ---------------------------------------------------------------------------


def test_get_user_by_username_found():
    """Returns user when username exists."""
    mock_db = MagicMock()
    mock_user = User(username="admin", email="admin@test.com")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = get_user_by_username(mock_db, "admin")
    assert result is mock_user


def test_get_user_by_username_not_found():
    """Returns None when username does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = get_user_by_username(mock_db, "nonexistent")
    assert result is None


# ---------------------------------------------------------------------------
# get_user_by_email
# ---------------------------------------------------------------------------


def test_get_user_by_email_found():
    """Returns user when email exists."""
    mock_db = MagicMock()
    mock_user = User(username="admin", email="admin@test.com")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = get_user_by_email(mock_db, "admin@test.com")
    assert result is mock_user


def test_get_user_by_email_not_found():
    """Returns None when email does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = get_user_by_email(mock_db, "no@test.com")
    assert result is None


# ---------------------------------------------------------------------------
# authenticate_user
# ---------------------------------------------------------------------------


def test_authenticate_user_success_by_username():
    """Authenticates with correct username + password."""
    mock_db = MagicMock()
    from passlib.context import CryptContext

    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash("testpass123")
    mock_user = User(username="admin", email="admin@test.com", hashed_password=hashed)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = authenticate_user(mock_db, "admin", "testpass123")
    assert result is mock_user


def test_authenticate_user_success_by_email():
    """Authenticates when username is actually an email."""
    mock_db = MagicMock()
    from passlib.context import CryptContext

    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash("testpass123")
    mock_user = User(username="admin", email="admin@test.com", hashed_password=hashed)

    mock_db.query.return_value.filter.return_value.first.side_effect = [None, mock_user]

    result = authenticate_user(mock_db, "admin@test.com", "testpass123")
    assert result is mock_user


def test_authenticate_user_wrong_password():
    """Returns False when password is incorrect."""
    mock_db = MagicMock()
    from passlib.context import CryptContext

    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash("testpass123")
    mock_user = User(username="admin", email="admin@test.com", hashed_password=hashed)

    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = authenticate_user(mock_db, "admin", "wrongpassword")
    assert result is False


def test_authenticate_user_not_found():
    """Returns False when user does not exist."""
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    result = authenticate_user(mock_db, "nonexistent", "testpass123")
    assert result is False


# ---------------------------------------------------------------------------
# create_password_reset_token
# ---------------------------------------------------------------------------


def test_create_password_reset_token():
    """Creates a valid reset token with correct claims."""
    token = create_password_reset_token("admin@test.com", 0)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["sub"] == "admin@test.com"
    assert payload["typ"] == TOKEN_TYPE_PASSWORD_RESET
    assert payload["ver"] == 0
    assert "exp" in payload


def test_create_password_reset_token_expires_in_15_minutes():
    """The reset token keeps its 15 minutes of life."""
    before = datetime.now(UTC)
    token = create_password_reset_token("admin@test.com", 0)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    after = datetime.now(UTC)
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    assert before + timedelta(minutes=15) - timedelta(seconds=5) <= exp
    assert exp <= after + timedelta(minutes=15) + timedelta(seconds=5)


def test_create_password_reset_token_is_bound_to_the_token_version():
    """The reset token carries the revocation counter of the account."""
    token = create_password_reset_token("admin@test.com", 5)
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload["ver"] == 5


# ---------------------------------------------------------------------------
# verify_password_reset_token
# ---------------------------------------------------------------------------


def test_verify_password_reset_token_valid():
    """Returns the claims of a valid reset token."""
    token = create_password_reset_token("admin@test.com", 2)
    claims = verify_password_reset_token(token)
    assert claims.email == "admin@test.com"
    assert claims.token_version == 2


def test_verify_password_reset_token_wrong_type():
    """Raises HTTPException when token type is not 'password_reset'."""
    user = User(id=7, username="admin", email="admin@test.com", token_version=0)
    token = create_access_token(user)
    with pytest.raises(HTTPException) as exc:
        verify_password_reset_token(token)
    assert exc.value.status_code == 400


def test_verify_password_reset_token_expired():
    """Raises HTTPException for expired token."""
    expire = datetime.now(UTC) - timedelta(minutes=1)
    to_encode = {
        "sub": "admin@test.com",
        "typ": TOKEN_TYPE_PASSWORD_RESET,
        "ver": 0,
        "exp": expire,
    }
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as exc:
        verify_password_reset_token(token)
    assert exc.value.status_code == 400


def test_verify_password_reset_token_invalid():
    """Raises HTTPException for malformed token."""
    with pytest.raises(HTTPException) as exc:
        verify_password_reset_token("not.a.valid.token")
    assert exc.value.status_code == 400


# ---------------------------------------------------------------------------
# get_current_active_user
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_current_active_user_active():
    """Returns user when is_active is True."""
    user = User(username="admin", is_active=True)
    result = await get_current_active_user(user)
    assert result is user


@pytest.mark.asyncio
async def test_get_current_active_user_inactive():
    """Raises HTTPException 401 when is_active is False.

    401 (not 400) so the frontend runs its sign-out flow and redirects to the
    login page instead of showing a generic error.
    """
    user = User(username="admin", is_active=False)
    with pytest.raises(HTTPException) as exc:
        await get_current_active_user(user)
    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# require_role
# ---------------------------------------------------------------------------


def test_require_role_allowed():
    """Returns user when role is in allowed list."""
    user = User(username="admin", role=UserRole.ADMIN)
    checker = require_role([UserRole.ADMIN, UserRole.MANAGER])
    result = checker(user)
    assert result is user


def test_require_role_denied():
    """Raises HTTPException when role is not allowed."""
    user = User(username="operator", role=UserRole.OPERATOR)
    checker = require_role([UserRole.ADMIN])
    with pytest.raises(HTTPException) as exc:
        checker(user)
    assert exc.value.status_code == 403
