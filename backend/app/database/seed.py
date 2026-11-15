from app.database.database import SessionLocal
from app.models.models import User, UserRole
from app.services.auth_service import get_password_hash
import asyncio
import os
import secrets


def _bootstrap_admin_password() -> tuple[str, bool]:
    """Return the password for the bootstrap admin account and whether it was generated.

    ``BOOTSTRAP_ADMIN_PASSWORD`` is used when the environment provides it.
    Otherwise a random password is generated and printed once to the startup
    log: a fresh database must never come up with a publicly known credential.
    """
    configured = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "").strip()
    if configured:
        return configured, False
    return secrets.token_urlsafe(16), True


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

        password, generated = _bootstrap_admin_password()

        print("Creating bootstrap admin user...")
        db.add(User(
            email="admin@thunderoll.com",
            username="admin",
            first_name="Admin",
            last_name="Usuario",
            role=UserRole.ADMIN,
            hashed_password=get_password_hash(password)
        ))
        db.commit()
        print("✅ Bootstrap admin user created successfully!")

        if generated:
            print(
                "🔑 Contraseña inicial del admin (se muestra una sola vez, "
                f"guárdala): {password}",
                flush=True,
            )

    except Exception as e:
        print(f"❌ Error creating demo data: {str(e)}", flush=True)
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(create_demo_data())
