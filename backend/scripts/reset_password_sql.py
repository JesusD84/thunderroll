#!/usr/bin/env python3
"""Break-glass: reset the password of a user straight in the database.

This is the escape hatch for the case the app cannot cover: every admin
account is locked out and nobody can sign in to reset a password from
Configuración. The script asks for the new password without echoing it,
hashes it with the same bcrypt setup the app uses, and prints the UPDATE
statement to run by hand.

It never connects to any database and never prints the password: run it
locally, then paste the statement into the Neon SQL editor
(Console → SQL Editor) or any psql session.

Usage:
    python backend/scripts/reset_password_sql.py
    python backend/scripts/reset_password_sql.py admin2@thunderoll.com
"""

import getpass
import re
import sys

from passlib.context import CryptContext

# Same hashing setup the app uses (app/core/security.py).
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MIN_PASSWORD_LENGTH = 8

# Conservative check: the email is interpolated into SQL, so anything with
# quotes or whitespace is rejected instead of escaped.
_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def validate_email(email: str) -> str:
    """Return the email or exit with an explanation."""
    email = email.strip()
    if not email:
        sys.exit("Se necesita el email del usuario.")
    if not _EMAIL_RE.match(email):
        sys.exit(f"Email con formato inesperado: {email!r}")
    return email


def validate_password(password: str, confirm: str) -> str:
    """Return the password or exit with an explanation."""
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    if password != confirm:
        sys.exit("Las contraseñas no coinciden.")
    return password


def build_update_sql(email: str, hashed_password: str) -> str:
    """Build the UPDATE statement that sets the new password hash."""
    return f"UPDATE users SET hashed_password = '{hashed_password}' WHERE email = '{email}';"


def main() -> None:
    default_email = sys.argv[1] if len(sys.argv) > 1 else None
    email = validate_email(default_email or input("Email del usuario: "))

    password = getpass.getpass(f"Nueva contraseña de {email} (mín. {MIN_PASSWORD_LENGTH} caracteres): ")
    confirm = getpass.getpass("Repite la nueva contraseña: ")
    validate_password(password, confirm)

    hashed = pwd_context.hash(password)

    print()
    print("Pega esta sentencia en el SQL Editor de Neon (o en una sesión psql):")
    print()
    print(build_update_sql(email, hashed))
    print()
    print("Después:")
    print("  1. Inicia sesión en la app con la nueva contraseña.")
    print("  2. Cámbiala desde Configuración → Mi cuenta para que solo tú la conozcas.")


if __name__ == "__main__":
    main()
