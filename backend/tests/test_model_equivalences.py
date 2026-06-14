"""Tests for model equivalences: resolution service + admin CRUD (TR-05)."""

import pytest

from app.models.models import ModelEquivalence, Unit, UnitStatus
from app.services import model_equivalence_service as service
from app.models import schemas


# --- Service: resolution -----------------------------------------------------


def test_resolve_returns_internal_model_when_mapping_exists(db_session):
    service.upsert_equivalence(db_session, "RESOLVE-A", "Internal A")
    assert service.resolve_internal_model(db_session, "RESOLVE-A") == "Internal A"


def test_resolve_is_case_and_whitespace_insensitive(db_session):
    service.upsert_equivalence(db_session, "RESOLVE-B", "Internal B")
    assert service.resolve_internal_model(db_session, "  resolve-b\n") == "Internal B"


def test_resolve_returns_none_when_unmapped_or_blank(db_session):
    assert service.resolve_internal_model(db_session, "DOES-NOT-EXIST-XYZ") is None
    assert service.resolve_internal_model(db_session, "") is None
    assert service.resolve_internal_model(db_session, None) is None


def test_upsert_is_idempotent_and_updates(db_session):
    first = service.upsert_equivalence(db_session, "UPSERT-A", "Old")
    second = service.upsert_equivalence(db_session, "UPSERT-A", "New")
    assert first.id == second.id
    assert service.resolve_internal_model(db_session, "UPSERT-A") == "New"


def test_list_unmapped_models(db_session):
    # A unit whose model has no equivalence shows up; one with an equivalence does not.
    db_session.add(Unit(
        engine_number="UNMAP-ENG-1", chassis_number="UNMAP-CHS-1",
        model="UNMAPPED-MODEL-1", brand="b", color="c",
        current_location_id=1, status=UnitStatus.AVAILABLE,
    ))
    db_session.add(Unit(
        engine_number="UNMAP-ENG-2", chassis_number="UNMAP-CHS-2",
        model="MAPPED-INTERNAL-1", brand="b", color="c",
        current_location_id=1, status=UnitStatus.AVAILABLE,
    ))
    db_session.commit()
    service.upsert_equivalence(db_session, "MAPPED-MANUF-1", "MAPPED-INTERNAL-1")

    unmapped = service.list_unmapped_models(db_session)
    assert "UNMAPPED-MODEL-1" in unmapped
    assert "MAPPED-INTERNAL-1" not in unmapped


# --- Endpoint: CRUD ----------------------------------------------------------


@pytest.mark.asyncio
async def test_create_and_get_equivalence(client, auth_headers, test_users, test_locations):
    payload = {"manufacturer_model": "EP-CREATE", "internal_model": "EP Internal"}
    resp = await client.post("/api/v1/model-equivalences/", json=payload, headers=auth_headers)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    assert created["manufacturer_model"] == "EP-CREATE"

    resp = await client.get(f"/api/v1/model-equivalences/{created['id']}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["internal_model"] == "EP Internal"


@pytest.mark.asyncio
async def test_create_duplicate_returns_409(client, auth_headers, test_users, test_locations):
    payload = {"manufacturer_model": "EP-DUP", "internal_model": "X"}
    r1 = await client.post("/api/v1/model-equivalences/", json=payload, headers=auth_headers)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/model-equivalences/", json=payload, headers=auth_headers)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_update_and_delete_equivalence(client, auth_headers, test_users, test_locations):
    payload = {"manufacturer_model": "EP-UPD", "internal_model": "Before"}
    created = (await client.post("/api/v1/model-equivalences/", json=payload, headers=auth_headers)).json()

    resp = await client.put(
        f"/api/v1/model-equivalences/{created['id']}",
        json={"internal_model": "After"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["internal_model"] == "After"

    resp = await client.delete(f"/api/v1/model-equivalences/{created['id']}", headers=auth_headers)
    assert resp.status_code == 200
    resp = await client.get(f"/api/v1/model-equivalences/{created['id']}", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_requires_auth(client):
    resp = await client.get("/api/v1/model-equivalences/")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_unmapped_endpoint_returns_list(client, auth_headers, test_users, test_locations):
    resp = await client.get("/api/v1/model-equivalences/unmapped", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
