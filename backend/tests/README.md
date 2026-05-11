# Backend Testing Guide

## Quick start

```bash
# Run all tests
docker compose exec backend python -m pytest tests/ -v

# Run a single test file
docker compose exec backend python -m pytest tests/test_auth_service.py -v

# Run with coverage (if pytest-cov installed)
docker compose exec backend python -m pytest tests/ --cov=app --cov-report=term-missing
```

## Test structure

```
tests/
├── conftest.py                # Shared fixtures (DB, client, auth headers)
├── test_auth.py                # Auth endpoint integration tests
├── test_auth_service.py        # Auth service unit tests (mocked DB)
├── test_user_repository.py     # User repository unit tests (mocked DB)
├── test_user_service.py        # User service unit tests (mocked DB)
├── test_users.py               # User endpoint integration tests
├── test_location_repository.py # Location repository unit tests (mocked DB)
├── test_location_service.py    # Location service unit tests (mocked DB)
├── test_locations.py           # Location endpoint integration tests
├── test_transfer_repository.py # Transfer repository unit tests (mocked DB)
├── test_transfer_service.py    # Transfer service unit tests (mocked DB)
├── test_transfers.py           # Transfer endpoint integration tests
├── test_unit_repository.py     # Unit repository unit tests (mocked DB)
├── test_unit_service.py        # Unit service unit tests (mocked DB)
├── test_units.py               # Units endpoint integration tests
├── test_reports.py             # Reports endpoint integration tests
└── README.md                   # This file
```

## Two types of tests

### 1. Unit tests (mocked DB)

Test individual service/repository functions in isolation. Use `unittest.mock.MagicMock` to simulate database calls.

**File naming**: `test_{module}_service.py` or `test_{module}_repository.py`

**Example** (`test_auth_service.py`):
```python
from unittest.mock import MagicMock
from app.services.auth_service import get_user_by_username
from app.models.models import User

def test_get_user_by_username_found():
    mock_db = MagicMock()
    mock_user = User(username="admin", email="admin@test.com")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_user

    result = get_user_by_username(mock_db, "admin")
    assert result is mock_user
```

**When to use**:
- Service layer functions that query the DB
- Repository functions
- Pure utility functions (no mocking needed)

### 2. Integration tests (real SQLite)

Test the full stack: HTTP request → endpoint → service → repository → database. Use the `client` fixture which provides an `httpx.AsyncClient` backed by an in-memory SQLite database.

**File naming**: `test_{resource}.py`

**Example** (`test_auth.py`):
```python
@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_users, test_locations):
    login_data = {"username": "admin", "password": "testpass123"}
    response = await client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
```

**When to use**:
- Testing endpoint behavior (auth, validation, response format)
- Testing end-to-end flows (create → read → update → delete)
- Testing authorization (role-based access)

## Fixtures

All fixtures are defined in `conftest.py`.

| Fixture | Scope | Description |
|---|---|---|
| `db_session` | session | Sync SQLAlchemy session (SQLite in-memory) |
| `client` | function | `httpx.AsyncClient` connected to the FastAPI app |
| `test_users` | session | 2 users: `admin` (ADMIN) and `inventario` (OPERATOR) |
| `test_locations` | session | 3 locations: Bodega, Taller, Sucursal |
| `auth_headers` | function | `Authorization: Bearer <token>` for the admin user |

### Adding seed data to a test

If you need additional data for a specific test, create it directly in the test using `db_session`:

```python
async def test_my_scenario(client, db_session):
    extra = MyModel(field="value")
    db_session.add(extra)
    db_session.commit()
    # ... test assertions
```

## Conventions

### Naming
- **Files**: `test_{what_youre_testing}.py`
- **Functions**: `test_{function_name}_{scenario}`
- **Docstrings**: First line describes what should happen

### Markers
- `@pytest.mark.asyncio` — required on every async test
- `@pytest.mark.skip(reason="...")` — for tests blocked by known issues

### Assertions
- Use plain `assert` statements (pytest rewrites them for rich output)
- Check status codes first, then response body
- For error cases, use `pytest.raises`:

```python
with pytest.raises(HTTPException) as exc:
    some_function(bad_input)
assert exc.value.status_code == 400
```

## Known limitations

- **4 tests skipped**: `test_reports.py` tests using `date_trunc` are skipped because SQLite doesn't support this PostgreSQL function. These will be fixed when the report service is made database-agnostic.
- **Sync SQLAlchemy**: The app uses synchronous SQLAlchemy. Tests match this — the `db_session` fixture provides a sync `Session`, and FastAPI handles running sync dependencies in async endpoints via threadpool.

## Adding new tests

1. Decide: unit test (mocked) or integration test (real DB)?
2. Create the file following the naming convention
3. Import fixtures from `conftest.py` as needed
4. Run `docker compose exec backend python -m pytest tests/ -v` to verify
5. Commit with prefix `test(backend):`
