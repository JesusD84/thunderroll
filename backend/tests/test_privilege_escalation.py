"""Regression tests for the privilege-escalation fix.

The bug: ``PUT /api/v1/user/me`` used the admin edit schema (``UserUpdate``),
which carries ``role`` and ``is_active``, and the repository wrote every
field it received with ``setattr``. Any operator could therefore promote
itself to admin.

These tests pin the fixed behaviour down:

* a self-update body that carries ``role``, ``is_active`` or an unknown
  field is rejected with 422 and the stored record does not change;
* the admin rules that were already in place keep working (managers only
  manage operators, an admin cannot remove their own role, deactivate or
  delete their own account);
* the other setattr-style endpoints do not let a lower role write a
  privileged field either.
"""

import pytest
from httpx import AsyncClient

from app.core.security import Security
from app.models.models import (
    Location,
    Transfer,
    TransferStatus,
    Unit,
    UnitStatus,
    User,
    UserRole,
)
from tests.conftest import TestingSessionLocal

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _login(
    client: AsyncClient, username: str, password: str = "testpass123"
) -> dict:
    response = await client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_user(username: str, role: UserRole = UserRole.OPERATOR) -> int:
    db = TestingSessionLocal()
    try:
        user = User(
            first_name="Test",
            last_name=username,
            username=username,
            email=f"{username}@test.com",
            hashed_password=Security.get_password_hash("testpass123"),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
    finally:
        db.close()


def _user_state(username: str) -> dict:
    """The stored record of a user, read straight from the database."""
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        assert user is not None, f"user {username} not found"
        return {
            "email": user.email,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active,
        }
    finally:
        db.close()


def _create_unit(engine_number: str) -> int:
    db = TestingSessionLocal()
    try:
        location = db.query(Location).first()
        unit = Unit(
            engine_number=engine_number,
            chassis_number=f"{engine_number}-CHS",
            model="EscModel",
            brand="EscBrand",
            color="ROJO",
            current_location_id=location.id,
            status=UnitStatus.AVAILABLE,
        )
        db.add(unit)
        db.commit()
        db.refresh(unit)
        return unit.id
    finally:
        db.close()


def _create_transfer(unit_id: int) -> int:
    db = TestingSessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        transfer = Transfer(
            unit_id=unit_id,
            dispatched_by_id=admin.id,
            origin_location_id=db.query(Location).first().id,
            destination_location_id=db.query(Location).all()[1].id,
            status=TransferStatus.IN_TRANSIT,
        )
        db.add(transfer)
        db.commit()
        db.refresh(transfer)
        return transfer.id
    finally:
        db.close()


def _transfer_state(transfer_id: int) -> dict:
    db = TestingSessionLocal()
    try:
        transfer = db.query(Transfer).filter(Transfer.id == transfer_id).first()
        assert transfer is not None
        return {
            "dispatched_by_id": transfer.dispatched_by_id,
            "dispatched_at": transfer.dispatched_at,
            "status": transfer.status,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# The regression itself: an operator cannot escalate through /user/me
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_operator_cannot_set_own_role_to_admin(
    client: AsyncClient, test_users, test_locations
):
    """``{"role": "admin"}`` on PUT /user/me is rejected and nothing changes."""
    headers = await _login(client, "inventario")
    before = _user_state("inventario")

    response = await client.put(
        "/api/v1/user/me", json={"role": "admin"}, headers=headers
    )

    assert response.status_code == 422, response.text
    assert _user_state("inventario") == before
    assert before["role"] == UserRole.OPERATOR


@pytest.mark.asyncio
async def test_operator_cannot_set_is_active_on_self(
    client: AsyncClient, test_users, test_locations
):
    """``{"is_active": true}`` on PUT /user/me is rejected and nothing changes."""
    headers = await _login(client, "inventario")
    before = _user_state("inventario")

    response = await client.put(
        "/api/v1/user/me", json={"is_active": True}, headers=headers
    )

    assert response.status_code == 422, response.text
    assert _user_state("inventario") == before


@pytest.mark.asyncio
async def test_escalation_attempt_does_not_apply_the_legitimate_field_either(
    client: AsyncClient, test_users, test_locations
):
    """A rejected body changes nothing at all, not even the allowed field."""
    headers = await _login(client, "inventario")
    before = _user_state("inventario")

    response = await client.put(
        "/api/v1/user/me",
        json={"first_name": "Escalado", "role": "admin"},
        headers=headers,
    )

    assert response.status_code == 422, response.text
    assert _user_state("inventario") == before


@pytest.mark.asyncio
async def test_manager_cannot_set_own_role_on_self_update(
    client: AsyncClient, test_users, test_locations
):
    """The rule is not operator-specific: no role can escalate through /me."""
    headers = await _login(client, "gerente")
    before = _user_state("gerente")

    response = await client.put(
        "/api/v1/user/me", json={"role": "admin"}, headers=headers
    )

    assert response.status_code == 422, response.text
    assert _user_state("gerente") == before


@pytest.mark.asyncio
async def test_admin_cannot_set_own_role_on_self_update(
    client: AsyncClient, test_users, test_locations
):
    """Even an admin cannot change a role through /me: that is /user/{id}."""
    headers = await _login(client, "admin")
    before = _user_state("admin")

    response = await client.put(
        "/api/v1/user/me", json={"role": "operator"}, headers=headers
    )

    assert response.status_code == 422, response.text
    assert _user_state("admin") == before


@pytest.mark.asyncio
async def test_self_update_rejects_unknown_field(
    client: AsyncClient, test_users, test_locations
):
    """An unknown field is a 422, not a silently ignored extra."""
    headers = await _login(client, "inventario")
    before = _user_state("inventario")

    response = await client.put(
        "/api/v1/user/me", json={"hashed_password": "forged"}, headers=headers
    )

    assert response.status_code == 422, response.text
    assert _user_state("inventario") == before


@pytest.mark.asyncio
async def test_operator_can_still_update_own_name(
    client: AsyncClient, test_users, test_locations
):
    """The legitimate self-service edit keeps working."""
    headers = await _login(client, "inventario")

    response = await client.put(
        "/api/v1/user/me", json={"first_name": "NuevoNombre"}, headers=headers
    )

    assert response.status_code == 200, response.text
    assert response.json()["first_name"] == "NuevoNombre"
    assert _user_state("inventario")["first_name"] == "NuevoNombre"


# ---------------------------------------------------------------------------
# The account identifiers are administrator-only
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_self_update_rejects_email(
    client: AsyncClient, test_users, test_locations
):
    """``email`` is administrator-only: /me refuses it and nothing changes."""
    headers = await _login(client, "inventario")
    before = _user_state("inventario")

    response = await client.put(
        "/api/v1/user/me", json={"email": "inventario.nuevo@test.com"}, headers=headers
    )

    assert response.status_code == 422, response.text
    assert _user_state("inventario") == before


@pytest.mark.asyncio
async def test_self_update_rejects_username(
    client: AsyncClient, test_users, test_locations
):
    """``username`` is administrator-only: /me refuses it and nothing changes."""
    headers = await _login(client, "inventario")
    before = _user_state("inventario")

    response = await client.put(
        "/api/v1/user/me", json={"username": "inventario_nuevo"}, headers=headers
    )

    assert response.status_code == 422, response.text
    assert _user_state("inventario") == before


@pytest.mark.asyncio
async def test_admin_can_still_change_another_user_email(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """The capability did not disappear: an admin edits the identifiers."""
    target_id = _create_user("email_target")

    response = await client.put(
        f"/api/v1/user/{target_id}",
        json={"email": "email_target.nuevo@test.com"},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text

    db = TestingSessionLocal()
    try:
        target = db.query(User).filter(User.id == target_id).first()
        assert target.email == "email_target.nuevo@test.com"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_admin_duplicate_email_returns_400(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """The uniqueness rule keeps guarding the admin flow."""
    target_id = _create_user("email_dup_target")

    response = await client.put(
        f"/api/v1/user/{target_id}",
        json={"email": "admin@test.com"},
        headers=auth_headers,
    )

    assert response.status_code == 400, response.text
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_duplicate_username_returns_400(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """The uniqueness rule keeps guarding the admin flow."""
    target_id = _create_user("username_dup_target")

    response = await client.put(
        f"/api/v1/user/{target_id}",
        json={"username": "admin"},
        headers=auth_headers,
    )

    assert response.status_code == 400, response.text
    assert "Username already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_self_update_with_null_name_returns_422(
    client: AsyncClient, test_users, test_locations
):
    """Nulling a NOT NULL column is a validation error, not a 500."""
    headers = await _login(client, "inventario")
    before = _user_state("inventario")

    response = await client.put(
        "/api/v1/user/me", json={"first_name": None}, headers=headers
    )

    assert response.status_code == 422, response.text
    assert _user_state("inventario") == before


# ---------------------------------------------------------------------------
# The admin rules that were already in place
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_own_account(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """An admin cannot lock themselves out by deactivating their own account."""
    me = (await client.get("/api/v1/user/me", headers=auth_headers)).json()
    before = _user_state("admin")

    response = await client.put(
        f"/api/v1/user/{me['id']}", json={"is_active": False}, headers=auth_headers
    )

    assert response.status_code == 400, response.text
    assert "cannot deactivate your own account" in response.json()["detail"]
    assert _user_state("admin") == before


@pytest.mark.asyncio
async def test_manager_can_only_manage_operators(
    client: AsyncClient, test_users, test_locations
):
    """Managers onboard operators; admins and managers are off limits."""
    _create_user("manager_scope", UserRole.MANAGER)
    headers = await _login(client, "manager_scope")

    operator = await client.post(
        "/api/v1/user/",
        json={
            "email": "scope_operator@test.com",
            "username": "scope_operator",
            "first_name": "Scope",
            "last_name": "Operator",
            "role": "operator",
            "password": "password123",
        },
        headers=headers,
    )
    assert operator.status_code == 201, operator.text

    for role in ("manager", "admin"):
        forbidden = await client.post(
            "/api/v1/user/",
            json={
                "email": f"scope_{role}@test.com",
                "username": f"scope_{role}",
                "first_name": "Scope",
                "last_name": role.capitalize(),
                "role": role,
                "password": "password123",
            },
            headers=headers,
        )
        assert forbidden.status_code == 403, forbidden.text
        assert "Operator role" in forbidden.json()["detail"]


@pytest.mark.asyncio
async def test_manager_cannot_edit_any_user(
    client: AsyncClient, test_users, test_locations
):
    """A manager has no path to change anyone's role or active status."""
    target_id = _create_user("manager_edit_target")
    _create_user("manager_editor", UserRole.MANAGER)
    headers = await _login(client, "manager_editor")

    response = await client.put(
        f"/api/v1/user/{target_id}",
        json={"role": "admin", "is_active": False},
        headers=headers,
    )

    assert response.status_code == 403, response.text

    db = TestingSessionLocal()
    try:
        target = db.query(User).filter(User.id == target_id).first()
        assert target.role == UserRole.OPERATOR
        assert target.is_active is not False
    finally:
        db.close()


@pytest.mark.asyncio
async def test_admin_cannot_remove_own_admin_role(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """The admin keeps their own role: no self-demotion through the admin flow."""
    me = (await client.get("/api/v1/user/me", headers=auth_headers)).json()
    before = _user_state("admin")

    response = await client.put(
        f"/api/v1/user/{me['id']}", json={"role": "operator"}, headers=auth_headers
    )

    assert response.status_code == 400, response.text
    assert "cannot remove your own Admin role" in response.json()["detail"]
    assert _user_state("admin") == before


# ---------------------------------------------------------------------------
# The other setattr-style endpoints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_operator_cannot_rewrite_the_dispatch_record(
    client: AsyncClient, test_users, test_locations
):
    """An operator receives units; it does not rewrite who dispatched them."""
    unit_id = _create_unit("MTX-ESC-001")
    transfer_id = _create_transfer(unit_id)
    headers = await _login(client, "inventario")
    before = _transfer_state(transfer_id)

    response = await client.put(
        f"/api/v1/transfers/{transfer_id}",
        json={"dispatched_by_id": 1},
        headers=headers,
    )

    assert response.status_code == 422, response.text
    assert _transfer_state(transfer_id) == before


@pytest.mark.asyncio
async def test_operator_cannot_rewrite_the_dispatch_timestamp(
    client: AsyncClient, test_users, test_locations
):
    """The dispatch timestamp belongs to the dispatch record as well."""
    unit_id = _create_unit("MTX-ESC-002")
    transfer_id = _create_transfer(unit_id)
    headers = await _login(client, "inventario")
    before = _transfer_state(transfer_id)

    response = await client.put(
        f"/api/v1/transfers/{transfer_id}",
        json={"dispatched_at": "2020-01-01T00:00:00"},
        headers=headers,
    )

    assert response.status_code == 422, response.text
    assert _transfer_state(transfer_id) == before


@pytest.mark.asyncio
async def test_operator_cannot_cancel_a_transfer(
    client: AsyncClient, test_users, test_locations
):
    """Confirming the arrival is allowed; cancelling is not."""
    unit_id = _create_unit("MTX-ESC-003")
    transfer_id = _create_transfer(unit_id)
    headers = await _login(client, "inventario")
    before = _transfer_state(transfer_id)

    response = await client.put(
        f"/api/v1/transfers/{transfer_id}",
        json={"status": "CANCELLED"},
        headers=headers,
    )

    assert response.status_code == 422, response.text
    assert _transfer_state(transfer_id) == before


@pytest.mark.asyncio
async def test_operator_can_confirm_the_arrival(
    client: AsyncClient, test_users, test_locations
):
    """The operator's own power still works: confirm the arrival."""
    unit_id = _create_unit("MTX-ESC-004")
    transfer_id = _create_transfer(unit_id)
    headers = await _login(client, "inventario")

    response = await client.put(
        f"/api/v1/transfers/{transfer_id}",
        json={"status": "RECEIVED"},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert _transfer_state(transfer_id)["status"] == TransferStatus.RECEIVED


@pytest.mark.asyncio
async def test_operator_cannot_forge_the_dispatcher_on_creation(
    client: AsyncClient, test_users, test_locations
):
    """Creating a transfer does not let an operator sign it as somebody else."""
    unit_id = _create_unit("MTX-ESC-005")
    headers = await _login(client, "inventario")

    response = await client.post(
        "/api/v1/transfers/",
        json={"unit_id": unit_id, "dispatched_by_id": 1},
        headers=headers,
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_manager_may_correct_the_dispatch_record(
    client: AsyncClient, test_users, test_locations
):
    """Managers keep the full transfer update: only operators are narrowed."""
    unit_id = _create_unit("MTX-ESC-006")
    transfer_id = _create_transfer(unit_id)
    headers = await _login(client, "gerente")

    response = await client.put(
        f"/api/v1/transfers/{transfer_id}",
        json={"status": "RECEIVED"},
        headers=headers,
    )

    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_update_schemas_reject_unknown_fields(
    client: AsyncClient, auth_headers, test_users, test_locations
):
    """The setattr-style endpoints only accept the fields they declare."""
    unit_id = _create_unit("MTX-ESC-007")

    unit_response = await client.put(
        f"/api/v1/units/{unit_id}",
        json={"not_a_unit_field": True},
        headers=auth_headers,
    )
    assert unit_response.status_code == 422, unit_response.text

    db = TestingSessionLocal()
    try:
        location_id = db.query(Location).first().id
    finally:
        db.close()

    location_response = await client.put(
        f"/api/v1/locations/{location_id}",
        json={"not_a_location_field": True},
        headers=auth_headers,
    )
    assert location_response.status_code == 422, location_response.text
