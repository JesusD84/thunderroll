import asyncio
import os

from app.database.database import SessionLocal
from app.models.models import User, UserRole
from app.services.auth_service import get_password_hash


def _bootstrap_admin_password() -> str | None:
    """The password for the bootstrap admin account, or None if it is not set.

    ``BOOTSTRAP_ADMIN_PASSWORD`` is the only way in. No password is ever
    generated: a generated one either ends up in the logs (which production
    keeps) or is a secret nobody knows, and an account whose password is
    unknown can neither be used nor recovered from the inside (changing your
    own password requires knowing the current one).

    Returns None when the variable is missing or empty.
    """
    return os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "").strip() or None


def create_demo_data():
    """Bootstrap a fresh database with a single admin account.

    Locations, units, transfers, other roles and model equivalences are NOT
    seeded: the client creates real ones themselves once they have the admin
    login, instead of inheriting placeholder demo data in a pilot environment.
    """
    db = SessionLocal()

    try:
        if db.query(User).first():
            print("Demo data already exists")
            return

        password = _bootstrap_admin_password()
        if password is None:
            # On purpose no admin is created: an account whose password nobody
            # knows cannot be used, and the only way to change it (the own
            # password change) needs the current one. The fix is one variable
            # and a restart.
            print(
                "⚠️  BOOTSTRAP_ADMIN_PASSWORD no está definida: no se creó la "
                "cuenta de admin. Definí la variable en el entorno y reiniciá "
                "la app para crearla (con la base vacía). No se genera ninguna "
                "contraseña: una que nadie conoce no sirve para entrar y no se "
                "puede cambiar desde adentro.",
                flush=True,
            )
            return

        print("Creating bootstrap admin user...")
        db.add(
            User(
                email="admin@thunderoll.com",
                username="admin",
                first_name="Admin",
                last_name="Usuario",
                role=UserRole.ADMIN,
                hashed_password=get_password_hash(password),
            )
        )
        db.commit()
        print("✅ Bootstrap admin user created successfully!")

    except Exception as e:
        print(f"❌ Error creating demo data: {str(e)}", flush=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(create_demo_data())
