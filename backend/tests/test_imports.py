"""Integration tests for import endpoints."""

import importlib
import io

import pytest
from httpx import AsyncClient
from openpyxl import Workbook

from app.api.v1.endpoints.imports import DEFAULT_BRAND, DEFAULT_COLOR
from app.models.models import Unit


def _make_xlsx(sheets: list[tuple[str, list[list]]]) -> bytes:
    """Build an in-memory .xlsx from ``[(sheet_name, rows), ...]``.

    ``rows`` are written verbatim (first row is whatever the test wants as a
    header). A ``None`` cell is left blank, which is how merged/empty cells read
    back, so it doubles as a way to exercise forward-fill.
    """
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets:
        ws = wb.create_sheet(title=name)
        for row in rows:
            ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def _upload(client, auth_headers, filename, content):
    files = {
        "file": (
            filename,
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    return await client.post("/api/v1/imports/upload", files=files, headers=auth_headers)


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


def test_xlrd_available_for_legacy_xls():
    """TR-03: xlrd must be installed so legacy .xls files can be parsed."""
    xlrd = importlib.import_module("xlrd")
    assert xlrd is not None


@pytest.mark.parametrize(
    ("filename", "expected_engine"),
    [
        ("inventory.xls", "xlrd"),
        ("INVENTORY.XLS", "xlrd"),
        ("inventory.xlsx", "openpyxl"),
        ("inventory.XLSX", "openpyxl"),
        ("inventory.xlsm", "openpyxl"),
    ],
)
def test_excel_engine_selection(filename, expected_engine):
    """TR-03: engine is selected explicitly by extension (case-insensitive)."""
    from app.api.v1.endpoints.imports import excel_engine_for

    assert excel_engine_for(filename) == expected_engine


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


# --- TR-04f: import endpoint uses the schema-tolerant parser end-to-end -------
#
# These exercise the full /upload flow against synthetic files that reproduce the
# real samples' quirks (English/Chinese headers, multiple sheets, model in merged
# cells, no identifier column). The 4 real supplier files are validated formally
# as fixtures in TR-09; here we prove the wiring without committing them.


@pytest.mark.asyncio
async def test_upload_english_headers_creates_units(
    client, auth_headers, test_users, test_locations, db_session
):
    """English headers map to canonical fields and persist correct values."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame No.", "Motor No.", "Color", "Model"],
            ["EN-FRAME-001", "EN-MOTOR-001", "Rojo", "X3"],
            ["EN-FRAME-002", "EN-MOTOR-002", "Negro", "X3"],
        ])
    ])
    resp = await _upload(client, auth_headers, "english.xlsx", content)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_records"] == 2
    assert body["successful_imports"] == 2
    assert body["failed_imports"] == 0

    unit = db_session.query(Unit).filter(Unit.chassis_number == "EN-FRAME-001").first()
    assert unit is not None
    assert unit.engine_number == "EN-MOTOR-001"
    assert unit.color == "Rojo"
    assert unit.model == "X3"
    assert unit.brand == DEFAULT_BRAND  # supplier files never carry a brand


@pytest.mark.asyncio
async def test_upload_chinese_headers_creates_units(
    client, auth_headers, test_users, test_locations, db_session
):
    """Chinese headers resolve to the same canonical fields."""
    content = _make_xlsx([
        ("库存", [
            ["车架号", "电机号", "颜色", "型号"],
            ["ZH-FRAME-001", "ZH-MOTOR-001", "蓝色", "xiaodou"],
        ])
    ])
    resp = await _upload(client, auth_headers, "chinese.xlsx", content)
    assert resp.status_code == 200, resp.text
    assert resp.json()["successful_imports"] == 1

    unit = db_session.query(Unit).filter(Unit.chassis_number == "ZH-FRAME-001").first()
    assert unit is not None
    assert unit.engine_number == "ZH-MOTOR-001"
    assert unit.color == "蓝色"
    assert unit.model == "xiaodou"


@pytest.mark.asyncio
async def test_upload_multisheet_uses_sheet_name_as_model(
    client, auth_headers, test_users, test_locations, db_session
):
    """Every data sheet is read; with no model column the sheet name is used."""
    content = _make_xlsx([
        ("diaoyu", [
            ["Frame", "Motor"],
            ["MS-FRAME-A1", "MS-MOTOR-A1"],
        ]),
        ("TY-D530", [
            ["Frame", "Motor"],
            ["MS-FRAME-B1", "MS-MOTOR-B1"],
            ["MS-FRAME-B2", "MS-MOTOR-B2"],
        ]),
    ])
    resp = await _upload(client, auth_headers, "multisheet.xlsx", content)
    assert resp.status_code == 200, resp.text
    assert resp.json()["successful_imports"] == 3

    a1 = db_session.query(Unit).filter(Unit.chassis_number == "MS-FRAME-A1").first()
    b2 = db_session.query(Unit).filter(Unit.chassis_number == "MS-FRAME-B2").first()
    assert a1.model == "diaoyu"
    assert b2.model == "TY-D530"


@pytest.mark.asyncio
async def test_upload_forward_fills_merged_model_cells(
    client, auth_headers, test_users, test_locations, db_session
):
    """A model present only on the first row of a block fills the whole block."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor", "Model"],
            ["MG-FRAME-001", "MG-MOTOR-001", "X3"],
            ["MG-FRAME-002", "MG-MOTOR-002", None],  # merged cell -> blank
            ["MG-FRAME-003", "MG-MOTOR-003", None],
        ])
    ])
    resp = await _upload(client, auth_headers, "merged.xlsx", content)
    assert resp.status_code == 200, resp.text
    assert resp.json()["successful_imports"] == 3

    for frame in ("MG-FRAME-001", "MG-FRAME-002", "MG-FRAME-003"):
        unit = db_session.query(Unit).filter(Unit.chassis_number == frame).first()
        assert unit is not None
        assert unit.model == "X3"


@pytest.mark.asyncio
async def test_upload_blank_rows_are_skipped(
    client, auth_headers, test_users, test_locations, db_session
):
    """Fully blank spacer rows are not counted as units; missing color defaults."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor", "Color"],
            ["BL-FRAME-001", "BL-MOTOR-001", None],
            [None, None, None],
            ["BL-FRAME-002", "BL-MOTOR-002", "Verde"],
        ])
    ])
    resp = await _upload(client, auth_headers, "blanks.xlsx", content)
    assert resp.status_code == 200, resp.text
    assert resp.json()["total_records"] == 2
    assert resp.json()["successful_imports"] == 2

    no_color = db_session.query(Unit).filter(Unit.chassis_number == "BL-FRAME-001").first()
    assert no_color.color == DEFAULT_COLOR


@pytest.mark.asyncio
async def test_upload_without_identifier_column_fails(
    client, auth_headers, test_users, test_locations
):
    """A file with no frame/motor column cannot identify units -> 500."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Color", "Model"],
            ["Rojo", "X3"],
        ])
    ])
    resp = await _upload(client, auth_headers, "no_id.xlsx", content)
    assert resp.status_code == 500
    assert "identifier" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_duplicate_rows_are_reported_not_fatal(
    client, auth_headers, test_users, test_locations, db_session
):
    """A duplicate identifier fails only its row; the rest still import."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor"],
            ["DUP-FRAME-001", "DUP-MOTOR-001"],
            ["DUP-FRAME-001", "DUP-MOTOR-002"],  # duplicate chassis
            ["DUP-FRAME-003", "DUP-MOTOR-003"],
        ])
    ])
    resp = await _upload(client, auth_headers, "dupes.xlsx", content)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_records"] == 3
    assert body["successful_imports"] == 2
    assert body["failed_imports"] == 1


@pytest.mark.asyncio
async def test_preview_reports_detected_fields(
    client, auth_headers, test_users, test_locations
):
    """Preview uses the parser and reports the canonical fields it detected."""
    content = _make_xlsx([
        ("Sheet1", [
            ["车架号", "电机号", "颜色", "型号"],
            ["PV-FRAME-001", "PV-MOTOR-001", "Gris", "X3"],
        ])
    ])
    files = {
        "file": (
            "preview.xlsx",
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    resp = await client.post("/api/v1/imports/preview", files=files, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["validation"]["is_valid"] is True
    assert set(body["detected_fields"]) == {"frame", "motor", "color", "model"}
    assert len(body["preview_data"]) == 1
