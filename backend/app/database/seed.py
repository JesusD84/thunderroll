from app.database.database import SessionLocal
from app.models.models import User, UserRole
from app.services.auth_service import get_password_hash
import asyncio


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

        print("Creating bootstrap admin user...")
        db.add(User(
            email="admin@thunderoll.com",
            username="admin",
            first_name="Admin",
            last_name="Usuario",
            role=UserRole.ADMIN,
            hashed_password=get_password_hash("admin123")
        ))
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
