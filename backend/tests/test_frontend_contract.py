"""Frontend-backend contract: the API returns what the UI reads.

The frontend reads typed JSON from the API. If one side renames a field and
the other does not, nothing fails: the unit tests mock both sides, and the
end-to-end tests mock the API as well. The UI then quietly renders empty
values in production.

This module closes that hole. It reads the TypeScript interfaces the
frontend declares and asserts that the real API response carries every field
the interface marks as required - the expectation is *derived from the
frontend*, not written by hand, so changing either side turns this red.

The counterpart on the frontend side is the end-to-end suite: it renders the
real pages against a mocked API, so between the two, both the shape and the
rendering are covered.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.models.models import (
    Import,
    ModelEquivalence,
    Transfer,
    TransferStatus,
    Unit,
    UnitStatus,
    User,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

_FIELD_RE = re.compile(r"^(\w+)(\?)?\s*:\s*(.*)$")


# ---------------------------------------------------------------------------
# Reading the TypeScript interfaces
# ---------------------------------------------------------------------------


def parse_interface(source: str, name: str) -> dict[str, dict]:
    """The fields a TypeScript interface declares.

    Returns ``{field: {"required": bool, "nested": {subfield: bool} | None}}``.
    Only one level of nesting is parsed, which is what the frontend uses.
    """
    match = re.search(rf"\binterface\s+{re.escape(name)}\s*\{{", source)
    assert match is not None, f"interface {name} not found in the frontend"

    depth = 1
    index = match.end()
    while index < len(source) and depth > 0:
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
        index += 1
    body = source[match.end() : index - 1]

    entries = []
    for raw in body.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("//") or stripped.startswith("*"):
            continue
        entries.append((len(raw) - len(raw.lstrip()), stripped))

    if not entries:
        return {}

    base_indent = min(indent for indent, _ in entries)
    fields: dict[str, dict] = {}
    current: str | None = None

    for indent, text in entries:
        parsed = _FIELD_RE.match(text)
        if parsed is None:
            continue
        key, optional, value = parsed.group(1), bool(parsed.group(2)), parsed.group(3)

        if indent == base_indent:
            nested = None
            inline = re.search(r"\{([^}]*)\}", value)
            if inline:
                nested = {}
                for part in inline.group(1).split(";"):
                    sub = _FIELD_RE.match(part.strip())
                    if sub:
                        # The flag is "optional"; the contract works with
                        # "required", so invert it.
                        nested[sub.group(1)] = not bool(sub.group(2))
            fields[key] = {"required": not optional, "nested": nested}
            current = key
        elif current is not None:
            # A block-nested field belongs to the last top-level one.
            if fields[current]["nested"] is None:
                fields[current]["nested"] = {}
            fields[current]["nested"][key] = not optional

    return fields


# ---------------------------------------------------------------------------
# The contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Contract:
    """One response the frontend reads."""

    name: str
    frontend_file: str
    interface: str
    method: str
    path: str
    is_list: bool = False


CONTRACTS: tuple[Contract, ...] = (
    Contract(
        "dashboard",
        "frontend/app/page.tsx",
        "DashboardData",
        "GET",
        "/api/v1/reports/dashboard",
    ),
    Contract(
        "units list",
        "frontend/app/units/page.tsx",
        "Unit",
        "GET",
        "/api/v1/units/",
        is_list=True,
    ),
    Contract(
        "unit detail",
        "frontend/app/units/[id]/page.tsx",
        "Unit",
        "GET",
        "/api/v1/units/{unit_id}",
    ),
    Contract(
        "unit transfers",
        "frontend/app/units/[id]/page.tsx",
        "Movement",
        "GET",
        "/api/v1/units/{unit_id}/transfers",
        is_list=True,
    ),
    Contract(
        "locations",
        "frontend/app/settings/page.tsx",
        "Location",
        "GET",
        "/api/v1/locations/",
        is_list=True,
    ),
    Contract(
        "users",
        "frontend/app/settings/page.tsx",
        "User",
        "GET",
        "/api/v1/user/",
        is_list=True,
    ),
    Contract(
        "transfers",
        "frontend/app/transfers/page.tsx",
        "Transfer",
        "GET",
        "/api/v1/transfers/",
        is_list=True,
    ),
    Contract(
        "model equivalences",
        "frontend/lib/imports.ts",
        "ModelEquivalence",
        "GET",
        "/api/v1/model-equivalences/",
        is_list=True,
    ),
    Contract(
        "imports",
        "frontend/lib/imports.ts",
        "ImportRecord",
        "GET",
        "/api/v1/imports/",
        is_list=True,
    ),
)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@pytest.fixture
def contract_resources(test_locations, db_session):
    """One unit (with a transfer), one equivalence and one import record.

    The list endpoints are checked against their first item, so each one
    needs at least one row to check.
    """
    suffix = uuid.uuid4().hex[:10]
    admin = db_session.query(User).filter(User.username == "admin").first()

    unit = Unit(
        engine_number=f"CT-ENG-{suffix}",
        chassis_number=f"CT-CHS-{suffix}",
        model="ContractModel",
        brand="ContractBrand",
        color="ROJO",
        current_location_id=test_locations[0].id,
        status=UnitStatus.AVAILABLE,
    )
    equivalence = ModelEquivalence(
        manufacturer_model=f"CT-MODEL-{suffix}",
        internal_model="ContractInternal",
    )
    import_record = Import(
        filename=f"uploads/contract_{suffix}.xlsx",
        original_filename=f"contract_{suffix}.xlsx",
        total_records=0,
        successful_imports=0,
        failed_imports=0,
        user_id=admin.id if admin else None,
        status="completed",
    )
    db_session.add_all([unit, equivalence, import_record])
    db_session.commit()
    for record in (unit, equivalence, import_record):
        db_session.refresh(record)

    transfer = Transfer(
        unit_id=unit.id,
        dispatched_by_id=admin.id if admin else None,
        origin_location_id=test_locations[0].id,
        destination_location_id=test_locations[1].id,
        status=TransferStatus.IN_TRANSIT,
    )
    db_session.add(transfer)
    db_session.commit()
    db_session.refresh(transfer)

    return {
        "unit_id": unit.id,
        "location_id": test_locations[0].id,
    }


# ---------------------------------------------------------------------------
# The test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "contract", CONTRACTS, ids=[contract.name for contract in CONTRACTS]
)
async def test_frontend_contract(
    contract: Contract,
    client: AsyncClient,
    auth_headers: dict,
    contract_resources: dict,
):
    """The real API response carries every field the frontend reads."""
    path = contract.path.format(**contract_resources)

    response = await client.request(contract.method, path, headers=auth_headers)
    assert response.status_code == 200, f"{contract.name}: {response.text}"

    payload = response.json()
    if contract.is_list:
        assert payload, f"{contract.name}: nothing to check the shape of"
        payload = payload[0]

    source = (REPO_ROOT / contract.frontend_file).read_text(encoding="utf-8")
    fields = parse_interface(source, contract.interface)

    missing: list[str] = []
    for field, spec in fields.items():
        if not spec["required"]:
            continue
        if field not in payload:
            missing.append(field)
            continue
        if not spec["nested"]:
            continue
        value = payload[field]
        if value is None:
            continue
        if isinstance(value, list):
            # An empty list says nothing about the shape of its items.
            if not value:
                continue
            value = value[0]
        if not isinstance(value, dict):
            continue
        for subfield, sub_required in spec["nested"].items():
            if sub_required and subfield not in value:
                missing.append(f"{field}.{subfield}")

    assert not missing, (
        f"{contract.name}: the API does not return the fields the frontend "
        f"reads ({contract.frontend_file} -> {contract.interface}): "
        f"{', '.join(missing)}"
    )
