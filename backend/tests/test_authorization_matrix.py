"""Authorization matrix: every protected endpoint, every role.

The expected access is not hardcoded in this file: it is read from the
backend itself. Each route declares the roles it accepts through the
``require_role`` dependency, and this module calls every protected endpoint
as admin, manager, operator and anonymously, asserting the status matches
that declaration:

* a role the route accepts -> the request goes through (its own success code)
* a role the route rejects -> 403
* no session at all        -> 401

The module also compares the backend matrix against the permission flags the
frontend uses (``frontend/lib/auth.ts``), so the UI and the API cannot drift
apart without the suite noticing.
"""

from __future__ import annotations

import io
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from httpx import AsyncClient
from openpyxl import Workbook

from app.core.security import Security
from app.main import app
from app.models.models import (
    Import,
    Location,
    ModelEquivalence,
    Transfer,
    TransferStatus,
    Unit,
    UnitStatus,
    User,
    UserRole,
)
from app.services.auth_service import get_current_active_user, get_current_user
from tests.conftest import TestingSessionLocal

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_AUTH_FILE = REPO_ROOT / "frontend" / "lib" / "auth.ts"

ROLES = ("admin", "manager", "operator", "anonymous")


# ---------------------------------------------------------------------------
# Reading the authorization rules out of the backend
# ---------------------------------------------------------------------------


def _normalize_path(path: str) -> str:
    """Collapse path parameters so two templates can be compared.

    ``/api/v1/user/{user_id}`` and ``/api/v1/user/{target_user_id}`` are the
    same route.
    """
    return re.sub(r"\{[^}]+\}", "{}", path)


def _find_route(method: str, path: str) -> APIRoute:
    """The route that serves ``method path``, matched on the path template."""
    wanted = _normalize_path(path)
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        if method not in route.methods:
            continue
        if _normalize_path(route.path) == wanted:
            return route
    raise AssertionError(f"Route not found in the app: {method} {path}")


def _required_roles(method: str, path: str) -> tuple[str, ...] | None:
    """The roles a route accepts, read from its ``require_role`` dependency.

    ``None`` means "any authenticated user": the route only requires a
    session, not a particular role.
    """
    route = _find_route(method, path)
    for dependency in route.dependant.dependencies:
        roles = getattr(dependency.call, "required_roles", None)
        if roles is not None:
            return tuple(role.value for role in roles)
    return None


def _requires_session(method: str, path: str) -> bool:
    """True when the route needs a signed-in user."""
    route = _find_route(method, path)

    def walk(dependant) -> bool:
        if dependant.call in (get_current_user, get_current_active_user):
            return True
        return any(walk(dependency) for dependency in dependant.dependencies)

    return walk(route.dependant)


# ---------------------------------------------------------------------------
# The matrix itself
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EndpointCase:
    """One protected endpoint and how to call it."""

    method: str
    path: str
    success_status: int = 200
    body: dict | Callable[[dict], dict] | None = None
    files: Callable[[dict], dict] | None = None

    def resolved_path(self, ctx: dict) -> str:
        return self.path.format(**ctx)

    def resolved_body(self, ctx: dict) -> dict | None:
        if self.body is None:
            return None
        if callable(self.body):
            return self.body(ctx)
        return self.body


def _xlsx_bytes(rows: list[list]) -> bytes:
    """A minimal workbook the import parser can read."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Hoja1"
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def _upload_files(ctx: dict) -> dict:
    content = _xlsx_bytes(
        [
            ["Frame No.", "Motor No.", "Color", "Model"],
            [f"MTX-FRAME-{ctx['suffix']}", f"MTX-MOTOR-{ctx['suffix']}", "Rojo", "X3"],
        ]
    )
    return {
        "file": (
            f"matrix_{ctx['suffix']}.xlsx",
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }


def _new_user_body(ctx: dict) -> dict:
    return {
        "email": f"matrix_{ctx['suffix']}@test.com",
        "username": f"matrix_{ctx['suffix']}",
        "first_name": "Matrix",
        "last_name": "User",
        "role": "operator",
        "password": "matrixpass123",
    }


def _new_unit_body(ctx: dict) -> dict:
    return {
        "model": "MatrixModel",
        "brand": "MatrixBrand",
        "color": "ROJO",
        "current_location_id": ctx["location_id"],
        "engine_number": f"MTX-NEW-ENG-{ctx['suffix']}",
        "chassis_number": f"MTX-NEW-CHS-{ctx['suffix']}",
    }


def _new_location_body(ctx: dict) -> dict:
    return {"name": f"Matrix Nueva {ctx['suffix']}", "address": "Calle Matrix"}


def _new_equivalence_body(ctx: dict) -> dict:
    return {
        "manufacturer_model": f"MTX-MODEL-{ctx['suffix']}",
        "internal_model": "MatrixInternal",
    }


def _new_transfer_body(ctx: dict) -> dict:
    return {
        "unit_id": ctx["unit_id"],
        "origin_location_id": ctx["location_id"],
        "destination_location_id": ctx["destination_location_id"],
    }


def _transfer_unit_body(ctx: dict) -> dict:
    return {"to_location_id": ctx["destination_location_id"]}


CASES: tuple[EndpointCase, ...] = (
    # --- users -------------------------------------------------------------
    EndpointCase("GET", "/api/v1/user/"),
    EndpointCase("POST", "/api/v1/user/", success_status=201, body=_new_user_body),
    EndpointCase("GET", "/api/v1/user/me"),
    EndpointCase("PUT", "/api/v1/user/me", body={"first_name": "Matrix"}),
    EndpointCase(
        "PUT",
        "/api/v1/user/me/password",
        success_status=204,
        body={"current_password": "testpass123", "new_password": "matrix-nueva-clave"},
    ),
    EndpointCase("PUT", "/api/v1/user/{target_user_id}", body={"first_name": "Matrix"}),
    EndpointCase("DELETE", "/api/v1/user/{target_user_id}", success_status=204),
    # --- units -------------------------------------------------------------
    EndpointCase("GET", "/api/v1/units/"),
    EndpointCase("POST", "/api/v1/units/", body=_new_unit_body),
    EndpointCase("GET", "/api/v1/units/stats"),
    EndpointCase("GET", "/api/v1/units/{unit_id}"),
    EndpointCase("PUT", "/api/v1/units/{unit_id}", body={"notes": "matrix"}),
    EndpointCase("DELETE", "/api/v1/units/{unit_id}"),
    EndpointCase("GET", "/api/v1/units/{unit_id}/transfers"),
    EndpointCase("POST", "/api/v1/units/{unit_id}/sell"),
    # --- locations ---------------------------------------------------------
    EndpointCase("GET", "/api/v1/locations/"),
    EndpointCase("POST", "/api/v1/locations/", body=_new_location_body),
    EndpointCase("GET", "/api/v1/locations/{location_id}"),
    EndpointCase(
        "PUT", "/api/v1/locations/{location_id}", body={"name": "Matrix Renombrada"}
    ),
    EndpointCase("DELETE", "/api/v1/locations/{empty_location_id}"),
    # --- imports -----------------------------------------------------------
    EndpointCase("GET", "/api/v1/imports/"),
    EndpointCase("GET", "/api/v1/imports/{import_id}"),
    EndpointCase("GET", "/api/v1/imports/{import_id}/errors"),
    EndpointCase("POST", "/api/v1/imports/upload", files=_upload_files),
    EndpointCase("POST", "/api/v1/imports/preview", files=_upload_files),
    EndpointCase("DELETE", "/api/v1/imports/{import_id}"),
    # --- model equivalences ------------------------------------------------
    EndpointCase("GET", "/api/v1/model-equivalences/"),
    EndpointCase("GET", "/api/v1/model-equivalences/unmapped"),
    EndpointCase(
        "POST",
        "/api/v1/model-equivalences/",
        success_status=201,
        body=_new_equivalence_body,
    ),
    EndpointCase("GET", "/api/v1/model-equivalences/{equivalence_id}"),
    EndpointCase(
        "PUT",
        "/api/v1/model-equivalences/{equivalence_id}",
        body={"internal_model": "MatrixInternalEditado"},
    ),
    EndpointCase("DELETE", "/api/v1/model-equivalences/{equivalence_id}"),
    # --- transfers ---------------------------------------------------------
    EndpointCase("GET", "/api/v1/transfers/stats"),
    EndpointCase("GET", "/api/v1/transfers/"),
    EndpointCase("POST", "/api/v1/transfers/", body=_new_transfer_body),
    EndpointCase("POST", "/api/v1/transfers/unit/{unit_id}", body=_transfer_unit_body),
    EndpointCase("GET", "/api/v1/transfers/unit/{unit_id}/active"),
    EndpointCase("GET", "/api/v1/transfers/{transfer_id}"),
    EndpointCase("PUT", "/api/v1/transfers/{transfer_id}", body={"status": "RECEIVED"}),
    EndpointCase("DELETE", "/api/v1/transfers/{transfer_id}"),
    # --- reports -----------------------------------------------------------
    EndpointCase("GET", "/api/v1/reports/dashboard"),
    EndpointCase("GET", "/api/v1/reports/inventory"),
    EndpointCase("GET", "/api/v1/reports/transfers"),
    EndpointCase("GET", "/api/v1/reports/sales"),
    EndpointCase("GET", "/api/v1/reports/export/inventory"),
    EndpointCase("GET", "/api/v1/reports/export/transfers"),
    EndpointCase("GET", "/api/v1/reports/export/sales"),
)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


def _build_context() -> dict:
    """Fresh resources for a single request.

    Every request gets its own location, unit, transfer and target user, so
    the matrix does not depend on the order the cases run in: a case that
    consumes its resource (sell, delete) cannot break the next role.
    """
    suffix = uuid.uuid4().hex[:10]
    db = TestingSessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()

        location = Location(name=f"Matrix Bodega {suffix}", address="Calle Matrix")
        empty_location = Location(
            name=f"Matrix Sucursal {suffix}", address="Calle Matrix"
        )
        db.add_all([location, empty_location])
        db.commit()
        db.refresh(location)
        db.refresh(empty_location)

        unit = Unit(
            engine_number=f"MTX-ENG-{suffix}",
            chassis_number=f"MTX-CHS-{suffix}",
            model="MatrixModel",
            brand="MatrixBrand",
            color="ROJO",
            current_location_id=location.id,
            status=UnitStatus.AVAILABLE,
        )
        db.add(unit)
        db.commit()
        db.refresh(unit)

        transfer = Transfer(
            unit_id=unit.id,
            dispatched_by_id=admin.id if admin else None,
            origin_location_id=location.id,
            destination_location_id=empty_location.id,
            status=TransferStatus.IN_TRANSIT,
            dispatched_at=datetime.now(UTC),
        )
        target_user = User(
            first_name="Matrix",
            last_name="Objetivo",
            username=f"matrix_target_{suffix}",
            email=f"matrix_target_{suffix}@test.com",
            hashed_password=Security.get_password_hash("testpass123"),
            role=UserRole.OPERATOR,
        )
        equivalence = ModelEquivalence(
            manufacturer_model=f"MTX-CTX-MODEL-{suffix}",
            internal_model="MatrixInternal",
        )
        import_record = Import(
            filename=f"uploads/matrix_{suffix}.xlsx",
            original_filename=f"matrix_{suffix}.xlsx",
            total_records=0,
            successful_imports=0,
            failed_imports=0,
            user_id=admin.id if admin else None,
            status="completed",
        )
        db.add_all([transfer, target_user, equivalence, import_record])
        db.commit()
        for record in (transfer, target_user, equivalence, import_record):
            db.refresh(record)

        return {
            "suffix": suffix,
            "location_id": location.id,
            "empty_location_id": empty_location.id,
            "destination_location_id": empty_location.id,
            "unit_id": unit.id,
            "transfer_id": transfer.id,
            "target_user_id": target_user.id,
            "equivalence_id": equivalence.id,
            "import_id": import_record.id,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# The matrix test
# ---------------------------------------------------------------------------


# The matrix calls every endpoint for every role, so the same three accounts
# would be logged in over and over. The tokens are stateless JWTs: one login
# per account is enough for the whole module.
_TOKEN_CACHE: dict[str, dict] = {}


async def _cached_login(client: AsyncClient, username: str) -> dict:
    if username not in _TOKEN_CACHE:
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": "testpass123"},
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        _TOKEN_CACHE[username] = {
            "Authorization": f"Bearer {response.json()['access_token']}"
        }
    return _TOKEN_CACHE[username]


@pytest.fixture
async def admin_headers(client: AsyncClient, test_users):
    """Session for the ADMIN role."""
    return await _cached_login(client, "admin")


@pytest.fixture
async def manager_headers(client: AsyncClient, test_users):
    """Session for the MANAGER role."""
    return await _cached_login(client, "gerente")


@pytest.fixture
async def operator_headers(client: AsyncClient, test_users):
    """Session for the OPERATOR role."""
    return await _cached_login(client, "inventario")


def _snapshot_shared_users() -> dict:
    """Read the shared accounts in their current state."""
    db = TestingSessionLocal()
    try:
        accounts = (
            db.query(User)
            .filter(User.username.in_(["admin", "gerente", "inventario"]))
            .all()
        )
        return {
            account.id: {
                "email": account.email,
                "username": account.username,
                "first_name": account.first_name,
                "last_name": account.last_name,
                "role": account.role,
                "is_active": account.is_active,
                "hashed_password": account.hashed_password,
            }
            for account in accounts
        }
    finally:
        db.close()


def _restore_shared_users(snapshot: dict) -> None:
    """Write the snapshot back with a fresh session.

    A fresh session is what makes this work: the session-scoped one still
    holds the pre-change values in its identity map, so setting them again
    would be a no-op and the change made through the API would survive.
    """
    db = TestingSessionLocal()
    try:
        for account_id, state in snapshot.items():
            account = db.query(User).filter(User.id == account_id).first()
            if account is None:
                continue
            for field_name, value in state.items():
                setattr(account, field_name, value)
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _restore_shared_users_fixture(db_session):
    """Leave the three shared accounts exactly as they were found.

    The matrix calls mutating endpoints (``/user/me``, ``/user/me/password``)
    on the session accounts, so every test restores their fields - password
    included - and expires the session-scoped identity map afterwards.
    """
    snapshot = _snapshot_shared_users()

    yield

    _restore_shared_users(snapshot)
    db_session.expire_all()


@pytest.mark.parametrize(
    "case", CASES, ids=[f"{case.method} {case.path}" for case in CASES]
)
@pytest.mark.parametrize("role", ROLES)
async def test_authorization_matrix(
    case: EndpointCase,
    role: str,
    client: AsyncClient,
    admin_headers: dict,
    manager_headers: dict,
    operator_headers: dict,
    monkeypatch,
    tmp_path,
):
    """Every protected endpoint, every role, against the declared rules."""
    # The upload endpoint writes into ./uploads: keep the workspace clean.
    monkeypatch.chdir(tmp_path)

    required_roles = _required_roles(case.method, case.path)
    headers = {
        "admin": admin_headers,
        "manager": manager_headers,
        "operator": operator_headers,
        "anonymous": {},
    }[role]

    ctx = _build_context()
    request_kwargs = {}
    body = case.resolved_body(ctx)
    if body is not None:
        request_kwargs["json"] = body
    if case.files is not None:
        request_kwargs["files"] = case.files(ctx)

    response = await client.request(
        case.method, case.resolved_path(ctx), headers=headers, **request_kwargs
    )

    if role == "anonymous":
        assert response.status_code == 401, (
            f"{case.method} {case.path} must answer 401 without a session, "
            f"got {response.status_code}"
        )
        return

    if required_roles is None or role in required_roles:
        assert response.status_code == case.success_status, (
            f"{role} is allowed on {case.method} {case.path} "
            f"(roles={required_roles}) but got {response.status_code}: {response.text}"
        )
    else:
        assert response.status_code == 403, (
            f"{role} must be rejected on {case.method} {case.path} "
            f"(roles={required_roles}) but got {response.status_code}: {response.text}"
        )


@pytest.mark.parametrize(
    "case", CASES, ids=[f"{case.method} {case.path}" for case in CASES]
)
def test_every_case_targets_a_protected_endpoint(case: EndpointCase):
    """The matrix only covers routes that need a session."""
    assert _requires_session(case.method, case.path), (
        f"{case.method} {case.path} is public and does not belong in the matrix"
    )


# ---------------------------------------------------------------------------
# Backend vs frontend
# ---------------------------------------------------------------------------


def _frontend_permission_flags() -> dict[str, str]:
    """The ``flag -> expression`` map declared in frontend/lib/auth.ts."""
    source = FRONTEND_AUTH_FILE.read_text(encoding="utf-8")
    block = re.search(r"return\s*\{(.*?)\n\s*\};", source, re.DOTALL)
    assert block, "Could not find the permission map in frontend/lib/auth.ts"

    flags: dict[str, str] = {}
    for line in block.group(1).splitlines():
        line = line.strip().rstrip(",")
        if not line or line.startswith("//") or ":" not in line:
            continue
        name, expression = line.split(":", 1)
        flags[name.strip()] = expression.strip()
    return flags


_EXPRESSION_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*(\s*(\|\||&&)\s*[A-Za-z_][A-Za-z0-9_]*)*$"
)


def _frontend_allows(flag: str, role: str, flags: dict[str, str]) -> bool:
    """Evaluate a frontend permission flag for a role."""
    expression = flags[flag]
    assert _EXPRESSION_PATTERN.match(expression), (
        f"Unexpected permission expression for {flag}: {expression}"
    )
    scope = {
        "isAdmin": role == "admin",
        "isManager": role == "manager",
        "isOperator": role == "operator",
    }
    # The frontend writes JavaScript; Python spells the same operators
    # differently.
    python_expression = expression.replace("||", " or ").replace("&&", " and ")
    return bool(eval(python_expression, {"__builtins__": {}}, scope))  # noqa: S307


# Each frontend flag maps to the backend route that carries the same meaning.
FRONTEND_FLAG_TO_BACKEND = {
    "viewEquivalences": ("GET", "/api/v1/model-equivalences/"),
    "manageEquivalences": ("POST", "/api/v1/model-equivalences/"),
    "deleteEquivalence": ("DELETE", "/api/v1/model-equivalences/{equivalence_id}"),
    "viewImports": ("GET", "/api/v1/imports/"),
    "uploadImport": ("POST", "/api/v1/imports/upload"),
    "deleteImport": ("DELETE", "/api/v1/imports/{import_id}"),
    "viewReports": ("GET", "/api/v1/reports/dashboard"),
    "manageUnits": ("POST", "/api/v1/units/"),
    "deleteUnit": ("DELETE", "/api/v1/units/{unit_id}"),
    "deleteTransfer": ("DELETE", "/api/v1/transfers/{transfer_id}"),
    "deleteLocation": ("DELETE", "/api/v1/locations/{location_id}"),
    "manageUsers": ("GET", "/api/v1/user/"),
}


@pytest.mark.parametrize("flag", sorted(FRONTEND_FLAG_TO_BACKEND))
@pytest.mark.parametrize("role", ("admin", "manager", "operator"))
def test_frontend_permissions_match_backend(flag: str, role: str):
    """The UI must hide exactly what the API rejects."""
    method, path = FRONTEND_FLAG_TO_BACKEND[flag]
    required_roles = _required_roles(method, path)
    assert required_roles is not None, f"{method} {path} should require a role"

    flags = _frontend_permission_flags()
    assert flag in flags, f"frontend/lib/auth.ts no longer declares {flag}"

    backend_allows = role in required_roles
    frontend_allows = _frontend_allows(flag, role, flags)
    assert frontend_allows == backend_allows, (
        f"{flag} diverges for role {role}: frontend says {frontend_allows}, "
        f"backend {method} {path} allows {sorted(required_roles)}"
    )
