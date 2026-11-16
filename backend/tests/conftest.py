"""Test configuration and fixtures.

Uses the real app models (app.models.models) with an in-memory SQLite database.
Sync engine matches production (app uses sync SQLAlchemy).
"""

import asyncio
import os
from collections.abc import Generator
from datetime import datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# La app exige configuración válida al importar (ver app/core/config.py):
# SECRET_KEY de 32 caracteres o más y DATABASE_URL. Se definen aquí, ANTES de
# importar nada de `app`, para que la suite siempre pueda arrancar.
#
# Estas variables tienen prioridad sobre el `.env` local del desarrollador:
# `load_dotenv` no sobrescribe lo que ya está en el entorno.
TEST_SECRET_KEY = "thunderoll-test-secret-key-only-for-the-test-suite"

os.environ["SECRET_KEY"] = TEST_SECRET_KEY

# La suite corre como desarrollo: los orígenes de localhost están en la lista
# de CORS solo cuando ENV=development (ver app/core/cors.py).
os.environ.setdefault("ENV", "development")

# La duración del token de acceso queda fijada aquí, como el valor que
# shippa el proyecto (60 minutos). Si el `.env` local del desarrollador
# dice otra cosa, la suite seguiría probando el valor de referencia.
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

# La URL que usa el motor real de la app (app.database.database). En la suite
# normal también es SQLite: los tests nunca deben tocar la base de datos real.
# La matriz de autorización contra PostgreSQL (RUN_POSTGRES_MATRIX=1) sí
# necesita la URL real del entorno, y en ese caso se respeta.
if os.getenv("RUN_POSTGRES_MATRIX") != "1" or not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.security import Security
from app.database.database import Base, get_db
from app.main import app
from app.models.models import (
    Location,
    Transfer,
    TransferStatus,
    Unit,
    UnitStatus,
    User,
    UserRole,
)

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
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Limpia el contador del limitador antes y después de cada prueba.

    El limitador guarda los conteos en memoria y los comparte toda la
    aplicación: sin esto, las pruebas que inician sesión irían gastando el
    límite por IP de las pruebas que vienen después.
    """
    from app.core.rate_limit import limiter

    limiter._storage.reset()
    yield
    limiter._storage.reset()


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
        # Appended last on purpose: other fixtures index this list by
        # position (test_users[0] is the admin).
        User(
            first_name="Test",
            last_name="Gerente",
            username="gerente",
            email="gerente@test.com",
            hashed_password=Security.get_password_hash("testpass123"),
            role=UserRole.MANAGER,
        ),
    ]
    for user in users:
        db_session.add(user)
    db_session.commit()
    for user in users:
        db_session.refresh(user)
    return users


async def _login(
    client: AsyncClient, username: str, password: str = "testpass123"
) -> dict:
    """Log in and return the Authorization header for that session."""
    response = await client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 200, f"Login failed for {username}: {response.text}"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
async def auth_headers(client: AsyncClient, test_users):
    """Admin session (historical name, kept so existing tests keep working)."""
    return await _login(client, "admin")


@pytest.fixture
async def admin_headers(client: AsyncClient, test_users):
    """Session for the ADMIN role."""
    return await _login(client, "admin")


@pytest.fixture
async def manager_headers(client: AsyncClient, test_users):
    """Session for the MANAGER role."""
    return await _login(client, "gerente")


@pytest.fixture
async def operator_headers(client: AsyncClient, test_users):
    """Session for the OPERATOR role."""
    return await _login(client, "inventario")


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
