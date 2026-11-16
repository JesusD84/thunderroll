"""Shared pieces of the authorization matrix.

The same table of protected endpoints runs twice:

* ``test_authorization_matrix.py`` against the in-memory SQLite database
  (fast, no infrastructure, the default);
* ``test_authorization_matrix_postgres.py`` against a real PostgreSQL, which
  is what production uses and which is stricter (enum types, case
  sensitivity, transactions).

Both modules use the cases, the resource builders and the assertions defined
here, so the two runs cannot drift apart.
"""

from __future__ import annotations

import io
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

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

ROLES = ("admin", "manager", "operator", "anonymous")

# The accounts the matrix logs in with, and the role each one plays.
ACCOUNTS = (
    ("admin", UserRole.ADMIN),
    ("gerente", UserRole.MANAGER),
    ("inventario", UserRole.OPERATOR),
)

ACCOUNT_PASSWORD = "testpass123"


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


def required_roles(method: str, path: str) -> tuple[str, ...] | None:
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


def requires_session(method: str, path: str) -> bool:
    """True when the route needs a signed-in user."""
    route = _find_route(method, path)

    def walk(dependant) -> bool:
        if dependant.call in (get_current_user, get_current_active_user):
            return True
        return any(walk(dependency) for dependency in dependant.dependencies)

    return walk(route.dependant)


# ---------------------------------------------------------------------------
# The cases
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


def build_context(session_factory) -> dict:
    """Fresh resources for a single request.

    Every request gets its own location, unit, transfer and target user, so
    the matrix does not depend on the order the cases run in: a case that
    consumes its resource (sell, delete) cannot break the next role.

    ``session_factory`` is the session maker of the database under test: the
    in-memory SQLite one for the default run, the real engine for the
    PostgreSQL one.
    """
    suffix = uuid.uuid4().hex[:10]
    db = session_factory()
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
            hashed_password=Security.get_password_hash(ACCOUNT_PASSWORD),
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


def ensure_accounts(session_factory) -> None:
    """Create the three accounts the matrix logs in with, if missing."""
    db = session_factory()
    try:
        for username, role in ACCOUNTS:
            if db.query(User).filter(User.username == username).first():
                continue
            db.add(
                User(
                    email=f"{username}@test.com",
                    username=username,
                    first_name="Test",
                    last_name=username.capitalize(),
                    hashed_password=Security.get_password_hash(ACCOUNT_PASSWORD),
                    role=role,
                )
            )
        db.commit()
    finally:
        db.close()


def snapshot_accounts(session_factory) -> dict:
    """Read the shared accounts in their current state."""
    db = session_factory()
    try:
        accounts = (
            db.query(User)
            .filter(User.username.in_([username for username, _ in ACCOUNTS]))
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


def restore_accounts(session_factory, snapshot: dict) -> None:
    """Write the snapshot back with a fresh session.

    A fresh session is what makes this work: a long-lived one still holds
    the pre-change values in its identity map, so setting them again would be
    a no-op and the change made through the API would survive.
    """
    db = session_factory()
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


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


async def login(client: AsyncClient, username: str, cache: dict) -> dict:
    """Log in and return the Authorization header, caching the token.

    The matrix calls every endpoint for every role, so the same accounts
    would be logged in over and over. The tokens are stateless JWTs: one
    login per account is enough for a whole run.
    """
    if username not in cache:
        response = await client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": ACCOUNT_PASSWORD},
        )
        assert response.status_code == 200, f"Login failed: {response.text}"
        cache[username] = {"Authorization": f"Bearer {response.json()['access_token']}"}
    return cache[username]


# ---------------------------------------------------------------------------
# The assertion
# ---------------------------------------------------------------------------


async def check_case(
    client: AsyncClient,
    case: EndpointCase,
    role: str,
    headers_by_role: dict,
    context_factory: Callable[[], dict],
) -> None:
    """Call one endpoint as one role and assert the status matches the rules.

    * a role the route accepts -> the request goes through (its own success code)
    * a role the route rejects -> 403
    * no session at all        -> 401
    """
    required = required_roles(case.method, case.path)
    headers = headers_by_role[role]

    ctx = context_factory()
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

    if required is None or role in required:
        assert response.status_code == case.success_status, (
            f"{role} is allowed on {case.method} {case.path} "
            f"(roles={required}) but got {response.status_code}: {response.text}"
        )
    else:
        assert response.status_code == 403, (
            f"{role} must be rejected on {case.method} {case.path} "
            f"(roles={required}) but got {response.status_code}: {response.text}"
        )
