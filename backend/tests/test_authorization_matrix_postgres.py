"""The authorization matrix against a real PostgreSQL.

Same table of endpoints as ``test_authorization_matrix.py``, but against the
database production actually uses. PostgreSQL is stricter than the in-memory
SQLite of the default run: enum types are real types, string comparison and
transactions behave differently, and the schema is created by the same
``create_all`` the app runs at startup.

Skipped unless it is explicitly asked for:

    RUN_POSTGRES_MATRIX=1 DATABASE_URL=postgresql://.../thunderoll_test \\
        pytest tests/test_authorization_matrix_postgres.py

Two independent guards, because this suite DELETEs units, transfers,
imports, equivalences and users:

1. it only runs when ``RUN_POSTGRES_MATRIX=1`` is set;
2. the database name must contain "test" (see ``assert_safe_test_database``).

The in-memory run is safe by construction - the database disappears with the
process - but a real one is not: a DATABASE_URL pointing at production would
destroy real records.
"""

from __future__ import annotations

import os

import pytest
from httpx import ASGITransport, AsyncClient

from app.database.database import Base, SessionLocal, engine, get_db
from app.main import app
from tests.authorization_matrix import (
    CASES,
    ROLES,
    EndpointCase,
    build_context,
    check_case,
    ensure_accounts,
    login,
    restore_accounts,
    snapshot_accounts,
)

# The suite only runs when it is explicitly asked for.
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_MATRIX") != "1",
    reason="Set RUN_POSTGRES_MATRIX=1 (with a PostgreSQL DATABASE_URL) to run it",
)


def assert_safe_test_database(url: str) -> None:
    """Fail loudly unless ``url`` points at a database that is safe to wipe.

    The database *name* must contain "test". That is the check that keeps
    this suite away from production (a Neon or Render URL names the real
    database) and from the local development database (docker-compose names
    it "thunderoll").
    """
    name = url.rsplit("/", 1)[-1].split("?")[0]
    if "test" not in name.lower():
        raise RuntimeError(
            "Refusing to run the destructive suite: the DATABASE_URL name must "
            f"contain 'test' (got {name!r})."
        )


@pytest.fixture(scope="module", autouse=True)
def real_database():
    """Run this module against the real engine instead of the in-memory one."""
    url = os.getenv("DATABASE_URL", "")
    if not url.startswith("postgres"):
        pytest.skip(f"DATABASE_URL is not a PostgreSQL URL: {url!r}")
    assert_safe_test_database(url)

    # The conftest replaces get_db with an in-memory SQLite for the whole
    # session; this module needs the real database, so the override is taken
    # out here and put back afterwards.
    saved_override = app.dependency_overrides.pop(get_db, None)

    Base.metadata.create_all(bind=engine)
    ensure_accounts(SessionLocal)

    yield

    if saved_override is not None:
        app.dependency_overrides[get_db] = saved_override


@pytest.fixture
async def client(real_database):
    """A client against the app, using the real database."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


_TOKEN_CACHE: dict[str, dict] = {}


@pytest.fixture
async def admin_headers(client: AsyncClient):
    """Session for the ADMIN role."""
    return await login(client, "admin", _TOKEN_CACHE)


@pytest.fixture
async def manager_headers(client: AsyncClient):
    """Session for the MANAGER role."""
    return await login(client, "gerente", _TOKEN_CACHE)


@pytest.fixture
async def operator_headers(client: AsyncClient):
    """Session for the OPERATOR role."""
    return await login(client, "inventario", _TOKEN_CACHE)


@pytest.fixture(autouse=True)
def _restore_shared_users_fixture():
    """Leave the three shared accounts exactly as they were found."""
    snapshot = snapshot_accounts(SessionLocal)

    yield

    restore_accounts(SessionLocal, snapshot)


@pytest.mark.parametrize(
    "case", CASES, ids=[f"{case.method} {case.path}" for case in CASES]
)
@pytest.mark.parametrize("role", ROLES)
async def test_authorization_matrix_postgres(
    case: EndpointCase,
    role: str,
    client: AsyncClient,
    admin_headers: dict,
    manager_headers: dict,
    operator_headers: dict,
    monkeypatch,
    tmp_path,
):
    """The same matrix, against PostgreSQL."""
    monkeypatch.chdir(tmp_path)

    await check_case(
        client,
        case,
        role,
        {
            "admin": admin_headers,
            "manager": manager_headers,
            "operator": operator_headers,
            "anonymous": {},
        },
        lambda: build_context(SessionLocal),
    )


def test_the_guard_rejects_a_database_that_is_not_a_test_one():
    """The guard is the reason this suite cannot wipe a real database."""
    from tests.test_authorization_matrix_postgres import assert_safe_test_database

    # A production-looking URL is refused.
    with pytest.raises(RuntimeError, match="test"):
        assert_safe_test_database("postgresql://u:p@ep-abc.neon.tech/thunderroll")

    # The local development database is refused too.
    with pytest.raises(RuntimeError, match="test"):
        assert_safe_test_database("postgresql://u:p@postgres:5432/thunderoll")

    # A database explicitly named as a test one is accepted.
    assert_safe_test_database("postgresql://u:p@localhost:5432/thunderoll_test")
