"""Test configuration and fixtures.

Uses the real app models (app.models.models) with an in-memory SQLite database.
Sync engine matches production (app uses sync SQLAlchemy).
"""

import pytest
import asyncio
from datetime import datetime
from typing import Generator
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database.database import Base, get_db
from app.models.models import User, UserRole, Location, Unit, Transfer, Import, ImportError
from app.models.models import UnitStatus, TransferStatus
from app.core.security import Security

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session")
def db_session(setup_database) -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
async def client(db_session) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
def test_locations(db_session: Session):
    locations = [
        Location(name="Test Bodega", address="Calle 1"),
        Location(name="Test Taller", address="Calle 2"),
        Location(name="Test Sucursal", address="Calle 3"),
    ]
    for loc in locations:
        db_session.add(loc)
    db_session.commit()
    for loc in locations:
        db_session.refresh(loc)
    return locations


@pytest.fixture(scope="session")
def test_users(db_session: Session):
    users = [
        User(
            first_name="Test",
            last_name="Admin",
            username="admin",
            email="admin@test.com",
            hashed_password=Security.get_password_hash("testpass123"),
            role=UserRole.ADMIN,
        ),
        User(
            first_name="Test",
            last_name="Inventario",
            username="inventario",
            email="inventario@test.com",
            hashed_password=Security.get_password_hash("testpass123"),
            role=UserRole.OPERATOR,
        ),
    ]
    for user in users:
        db_session.add(user)
    db_session.commit()
    for user in users:
        db_session.refresh(user)
    return users


@pytest.fixture
async def auth_headers(client: AsyncClient, test_users):
    login_data = {"username": "admin", "password": "testpass123"}
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200, f"Login failed: {response.text}"
    token_data = response.json()
    return {"Authorization": f"Bearer {token_data['access_token']}"}


@pytest.fixture
def sold_unit_with_history(test_users, test_locations):
    """Create a SOLD unit (with sold_date) and a transfer (with dispatched_at).

    This exercises the month aggregations in the report service, which group by
    a substr(cast(date, String)) expression that already returns a 'YYYY-MM'
    string. Regression coverage for the bug where the service called .strftime()
    on that string, raising AttributeError -> 500. Function-scoped and cleaned up
    so it does not leak into other tests.
    """
    db = TestingSessionLocal()
    unit = Unit(
        engine_number="REG-ENG-001",
        chassis_number="REG-CHS-001",
        brand="RegressionBrand",
        model="RegModel",
        color="Negro",
        current_location_id=test_locations[0].id,
        status=UnitStatus.SOLD,
        sold_date=datetime.now(),
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)

    transfer = Transfer(
        unit_id=unit.id,
        dispatched_by_id=test_users[0].id,
        destination_location_id=test_locations[0].id,
        status=TransferStatus.RECEIVED,
        dispatched_at=datetime.now(),
        received_at=datetime.now(),
    )
    db.add(transfer)
    db.commit()
    db.refresh(transfer)

    yield unit, transfer

    db.delete(transfer)
    db.delete(unit)
    db.commit()
    db.close()
