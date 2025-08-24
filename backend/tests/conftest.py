
"""Test configuration and fixtures."""

import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.base import Base
from app.core.deps import get_db
from app.models.user import User, UserRole
from app.models.location import Location, LocationType
from app.core.security import get_password_hash

# Test database URL (in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create test session maker
TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


# Override the dependency
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database():
    """Create test database tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(setup_database) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def test_locations(db_session: AsyncSession):
    """Create test locations."""
    locations = [
        Location(name="Test Bodega", type=LocationType.BODEGA, active=True),
        Location(name="Test Taller", type=LocationType.TALLER, active=True),
        Location(name="Test Sucursal", type=LocationType.SUCURSAL, active=True),
    ]
    
    for location in locations:
        db_session.add(location)
    
    await db_session.commit()
    
    for location in locations:
        await db_session.refresh(location)
    
    return locations


@pytest.fixture
async def test_users(db_session: AsyncSession):
    """Create test users."""
    users = [
        User(
            name="Test Admin",
            email="admin@test.com",
            password_hash=get_password_hash("testpass123"),
            role=UserRole.ADMIN
        ),
        User(
            name="Test Inventario",
            email="inventario@test.com", 
            password_hash=get_password_hash("testpass123"),
            role=UserRole.INVENTARIO
        ),
    ]
    
    for user in users:
        db_session.add(user)
    
    await db_session.commit()
    
    for user in users:
        await db_session.refresh(user)
    
    return users


@pytest.fixture
async def auth_headers(client: AsyncClient, test_users):
    """Get authentication headers for admin user."""
    login_data = {
        "email": "admin@test.com",
        "password": "testpass123"
    }
    
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    
    token_data = response.json()
    return {"Authorization": f"Bearer {token_data['access_token']}"}
