"""Tests of the bootstrap admin account.

The seed is what creates the first admin of a fresh database, so it is the
place where a credential can leak: into the logs (which production keeps) or
into the repository (which is public).

These tests run against a private in-memory database, so they never touch the
development or production data.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import seed
from app.models.models import Base, User, UserRole
from app.services.auth_service import verify_password

BOOTSTRAP_EMAIL = "admin@thunderoll.com"
BOOTSTRAP_USERNAME = "admin"


@pytest.fixture
def seed_db(monkeypatch):
    """Point the seed at a private in-memory database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr(seed, "SessionLocal", session_factory)
    return session_factory


@pytest.fixture(autouse=True)
def _no_bootstrap_password_in_the_environment(monkeypatch):
    """Start every test without the variable, so each one sets what it needs."""
    monkeypatch.delenv("BOOTSTRAP_ADMIN_PASSWORD", raising=False)


def _users(session_factory) -> list[User]:
    db = session_factory()
    try:
        return db.query(User).all()
    finally:
        db.close()


def test_admin_is_created_with_the_configured_password(seed_db, monkeypatch, capsys):
    """With the variable set, the account exists and that password works."""
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "testpass123")

    seed.create_demo_data()

    users = _users(seed_db)
    assert len(users) == 1
    admin = users[0]
    assert admin.username == BOOTSTRAP_USERNAME
    assert admin.email == BOOTSTRAP_EMAIL
    assert admin.role == UserRole.ADMIN
    assert verify_password("testpass123", admin.hashed_password)


def test_no_admin_is_created_without_the_password(seed_db, capsys):
    """Without the variable, no account is created at all.

    An account whose password nobody knows cannot be used, and it cannot be
    recovered from the inside either: changing your own password requires
    knowing the current one.
    """
    seed.create_demo_data()

    assert _users(seed_db) == []
    output = capsys.readouterr().out
    assert "BOOTSTRAP_ADMIN_PASSWORD" in output


def test_the_seed_never_prints_a_password(seed_db, monkeypatch, capsys):
    """No password reaches the log, with or without the variable.

    The logs of production are kept: a password printed there is a password
    published.
    """
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "testpass123")
    seed.create_demo_data()
    output = capsys.readouterr().out
    assert "testpass123" not in output

    # And the hash never reaches the log either.
    admin = _users(seed_db)[0]
    assert admin.hashed_password not in output


def test_the_warning_explains_how_to_fix_it(seed_db, capsys):
    """The warning says what is missing and what to do about it."""
    seed.create_demo_data()

    output = capsys.readouterr().out
    assert "BOOTSTRAP_ADMIN_PASSWORD" in output
    # It has to say how to get an admin, not only that something went wrong.
    assert "reinici" in output.lower()


def test_the_seed_is_idempotent(seed_db, monkeypatch, capsys):
    """Running it twice does not fail nor create a second account."""
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "testpass123")

    seed.create_demo_data()
    seed.create_demo_data()

    assert len(_users(seed_db)) == 1
    assert "already exists" in capsys.readouterr().out
