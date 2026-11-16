"""Tests for the break-glass password reset script."""

import pytest

from scripts.reset_password_sql import (
    MIN_PASSWORD_LENGTH,
    build_update_sql,
    validate_email,
    validate_password,
)


def test_build_update_sql_targets_the_user():
    sql = build_update_sql("admin2@thunderoll.com", "$2b$12$hash")
    assert sql == (
        "UPDATE users SET hashed_password = '$2b$12$hash' WHERE email = 'admin2@thunderoll.com';"
    )


def test_validate_email_accepts_a_normal_address():
    assert validate_email("  admin2@thunderoll.com ") == "admin2@thunderoll.com"


@pytest.mark.parametrize(
    "email",
    ["", "   ", "no-es-email", "a@b", "x'; DROP TABLE users;--@evil.com", "a b@c.com"],
)
def test_validate_email_rejects_unsafe_values(email):
    """Anything that could break the SQL statement is rejected, not escaped."""
    with pytest.raises(SystemExit):
        validate_email(email)


def test_validate_password_requires_the_minimum_length():
    with pytest.raises(SystemExit):
        validate_password("corta", "corta")


def test_validate_password_requires_both_to_match():
    with pytest.raises(SystemExit):
        validate_password("clave-larga-1", "otra-clave-2")


def test_validate_password_accepts_a_long_enough_matching_pair():
    assert validate_password("clave-larga-1", "clave-larga-1") == "clave-larga-1"


def test_hash_never_contains_the_plain_password():
    """The bcrypt hash the script embeds in the SQL must not leak the password."""
    from passlib.context import CryptContext

    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    plaintext = "clave-larga-1"
    hashed = ctx.hash(plaintext)
    assert plaintext not in hashed
    assert hashed.startswith("$2")
    assert MIN_PASSWORD_LENGTH == 8
