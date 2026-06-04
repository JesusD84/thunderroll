"""Integration tests for import endpoints."""

import importlib

import pytest
from httpx import AsyncClient


def test_canonical_model_is_models_module():
    """TR-01: app.models.models is the canonical source of truth.

    The active import endpoint and seed/repositories all use this module, and
    the app creates its tables from `models.Base.metadata`. This guards the
    decision against regressions (e.g. reintroducing the alternate model set).
    """
    from app.models.models import Unit

    columns = Unit.__table__.columns
    # engine_number is a string (alphanumeric supplier values), not BigInteger.
    assert str(columns["engine_number"].type).upper().startswith("VARCHAR")
    assert "brand" in columns
    assert "color" in columns


@pytest.mark.parametrize(
    "module_name",
    [
        "app.services.import_excel",
        "app.schemas.shipment",
        "app.schemas.unit_event",
    ],
)
def test_dead_modules_removed(module_name):
    """TR-02: broken/dead modules must stay deleted.

    These referenced non-existent models (app.models.unit/shipment/unit_event)
    and were never wired into the running app.
    """
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


@pytest.mark.asyncio
async def test_get_imports(client: AsyncClient, auth_headers, test_users, test_locations):
    """Authenticated user can list imports."""
    response = await client.get("/api/v1/imports/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_imports_unauthorized(client: AsyncClient):
    """Unauthenticated request returns 401."""
    response = await client.get("/api/v1/imports/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_import_not_found(client: AsyncClient, auth_headers, test_users, test_locations):
    """Returns 404 for non-existent import."""
    response = await client.get("/api/v1/imports/9999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_import_errors_empty(client: AsyncClient, auth_headers, test_users, test_locations):
    """Returns empty list for import with no errors."""
    response = await client.get("/api/v1/imports/9999/errors", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_preview_invalid_file_type(client: AsyncClient, auth_headers, test_users, test_locations):
    """Preview of non-Excel/CSV file returns 400."""
    files = {"file": ("test.txt", b"content", "text/plain")}
    response = await client.post("/api/v1/imports/preview", files=files, headers=auth_headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_invalid_file_type(client: AsyncClient, auth_headers, test_users, test_locations):
    """Upload of non-Excel/CSV file returns 400."""
    files = {"file": ("test.txt", b"content", "text/plain")}
    response = await client.post("/api/v1/imports/upload", files=files, headers=auth_headers)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_import_not_found(client: AsyncClient, auth_headers, test_users, test_locations):
    """Returns 404 when deleting non-existent import."""
    response = await client.delete("/api/v1/imports/9999", headers=auth_headers)
    assert response.status_code == 404
