"""Authorization matrix: every protected endpoint, every role.

The expected access is not hardcoded in this file: it is read from the
backend itself. Each route declares the roles it accepts through the
``require_role`` dependency, and this module calls every protected endpoint
as admin, manager, operator and anonymously, asserting the status matches
that declaration:

* a role the route accepts -> the request goes through (its own success code)
* a role the route rejects -> 403
* no session at all        -> 401

This run uses the in-memory SQLite database, so it needs no infrastructure.
The same matrix runs against a real PostgreSQL in
``test_authorization_matrix_postgres.py``; the table of cases lives in
``tests/authorization_matrix.py`` so the two cannot drift apart.

The module also compares the backend matrix against the permission flags the
frontend uses (``frontend/lib/auth.ts``), so the UI and the API cannot drift
apart without the suite noticing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from httpx import AsyncClient

from tests.authorization_matrix import (
    CASES,
    ROLES,
    EndpointCase,
    build_context,
    check_case,
    login,
    requires_session,
    restore_accounts,
    snapshot_accounts,
)
from tests.conftest import TestingSessionLocal

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_AUTH_FILE = REPO_ROOT / "frontend" / "lib" / "auth.ts"


# ---------------------------------------------------------------------------
# The matrix test
# ---------------------------------------------------------------------------


# The matrix calls every endpoint for every role, so the same three accounts
# would be logged in over and over. The tokens are stateless JWTs: one login
# per account is enough for the whole module.
_TOKEN_CACHE: dict[str, dict] = {}


@pytest.fixture
async def admin_headers(client: AsyncClient, test_users):
    """Session for the ADMIN role."""
    return await login(client, "admin", _TOKEN_CACHE)


@pytest.fixture
async def manager_headers(client: AsyncClient, test_users):
    """Session for the MANAGER role."""
    return await login(client, "gerente", _TOKEN_CACHE)


@pytest.fixture
async def operator_headers(client: AsyncClient, test_users):
    """Session for the OPERATOR role."""
    return await login(client, "inventario", _TOKEN_CACHE)


@pytest.fixture(autouse=True)
def _restore_shared_users_fixture(db_session):
    """Leave the three shared accounts exactly as they were found.

    The matrix calls mutating endpoints (``/user/me``, ``/user/me/password``)
    on the session accounts, so every test restores their fields - password
    included - and expires the session-scoped identity map afterwards.
    """
    snapshot = snapshot_accounts(TestingSessionLocal)

    yield

    restore_accounts(TestingSessionLocal, snapshot)
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
    # The upload endpoint stores the file: keep the workspace clean.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("IMPORT_STORAGE_DIR", str(tmp_path / "imports"))

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
        lambda: build_context(TestingSessionLocal),
    )


@pytest.mark.parametrize(
    "case", CASES, ids=[f"{case.method} {case.path}" for case in CASES]
)
def test_every_case_targets_a_protected_endpoint(case: EndpointCase):
    """The matrix only covers routes that need a session."""
    assert requires_session(case.method, case.path), (
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
    from tests.authorization_matrix import required_roles

    method, path = FRONTEND_FLAG_TO_BACKEND[flag]
    required = required_roles(method, path)
    assert required is not None, f"{method} {path} should require a role"

    flags = _frontend_permission_flags()
    assert flag in flags, f"frontend/lib/auth.ts no longer declares {flag}"

    backend_allows = role in required
    frontend_allows = _frontend_allows(flag, role, flags)
    assert frontend_allows == backend_allows, (
        f"{flag} diverges for role {role}: frontend says {frontend_allows}, "
        f"backend {method} {path} allows {sorted(required)}"
    )
