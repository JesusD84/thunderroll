"""Integration tests for import endpoints."""

import importlib
import io
import json

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


async def _upload(client, auth_headers, filename, content, data=None):
    files = {
        "file": (
            filename,
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    return await client.post(
        "/api/v1/imports/upload", files=files, data=data, headers=auth_headers
    )


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


# --- TR-08: atomic batch import, per-row errors, authenticated transfer owner -


@pytest.mark.asyncio
async def test_upload_transfer_uses_authenticated_user(
    client, auth_headers, test_users, test_locations, db_session
):
    """The inbound transfer is owned by the authenticated user, not a hardcoded id."""
    from app.models.models import User, Transfer

    admin = db_session.query(User).filter(User.username == "admin").first()
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor"],
            ["AUTH-FRAME-001", "AUTH-MOTOR-001"],
        ])
    ])
    resp = await _upload(client, auth_headers, "auth.xlsx", content)
    assert resp.status_code == 200, resp.text

    unit = db_session.query(Unit).filter(Unit.chassis_number == "AUTH-FRAME-001").first()
    transfer = db_session.query(Transfer).filter(Transfer.unit_id == unit.id).first()
    assert transfer is not None
    assert transfer.dispatched_by_id == admin.id


@pytest.mark.asyncio
async def test_upload_records_per_row_error_details(
    client, auth_headers, test_users, test_locations, db_session
):
    """Failed rows are logged in ImportError with row number + raw data."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor"],
            ["ERR-FRAME-001", "ERR-MOTOR-001"],
            ["ERR-FRAME-001", "ERR-MOTOR-002"],  # duplicate chassis -> error row
        ])
    ])
    resp = await _upload(client, auth_headers, "errdetail.xlsx", content)
    assert resp.status_code == 200, resp.text
    import_id = resp.json()["import_id"]

    errors_resp = await client.get(
        f"/api/v1/imports/{import_id}/errors", headers=auth_headers
    )
    assert errors_resp.status_code == 200
    errors = errors_resp.json()
    assert len(errors) == 1
    err = errors[0]
    assert err["row_number"] == 2
    assert "already exists" in err["error_message"]
    assert "ERR-FRAME-001" in err["raw_data"]


@pytest.mark.asyncio
async def test_upload_existing_db_unit_blocks_duplicate_row(
    client, auth_headers, test_users, test_locations, db_session
):
    """A row matching a unit already in the DB is reported, others still import."""
    first = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor"],
            ["PERSIST-FRAME-001", "PERSIST-MOTOR-001"],
        ])
    ])
    assert (await _upload(client, auth_headers, "first.xlsx", first)).status_code == 200

    second = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor"],
            ["PERSIST-FRAME-001", "PERSIST-MOTOR-999"],  # chassis already in DB
            ["PERSIST-FRAME-002", "PERSIST-MOTOR-002"],
        ])
    ])
    resp = await _upload(client, auth_headers, "second.xlsx", second)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_records"] == 2
    assert body["successful_imports"] == 1
    assert body["failed_imports"] == 1


@pytest.mark.asyncio
async def test_upload_applies_model_equivalence(
    client, auth_headers, test_users, test_locations, db_session
):
    """TR-05: a mapped manufacturer model is stored as the internal model."""
    from app.services import model_equivalence_service as me_service

    me_service.upsert_equivalence(db_session, "X3-TR05", "Triciclo Interno X3")
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor", "Model"],
            ["EQ-FRAME-001", "EQ-MOTOR-001", "X3-TR05"],
        ])
    ])
    resp = await _upload(client, auth_headers, "equiv.xlsx", content)
    assert resp.status_code == 200, resp.text
    assert resp.json()["successful_imports"] == 1

    unit = db_session.query(Unit).filter(Unit.chassis_number == "EQ-FRAME-001").first()
    assert unit.model == "Triciclo Interno X3"


@pytest.mark.asyncio
async def test_upload_keeps_manufacturer_model_when_unmapped(
    client, auth_headers, test_users, test_locations, db_session
):
    """TR-05: with no equivalence the manufacturer model is kept as-is."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor", "Model"],
            ["EQ-FRAME-002", "EQ-MOTOR-002", "UNMAPPED-TR05"],
        ])
    ])
    resp = await _upload(client, auth_headers, "noequiv.xlsx", content)
    assert resp.status_code == 200, resp.text

    unit = db_session.query(Unit).filter(Unit.chassis_number == "EQ-FRAME-002").first()
    assert unit.model == "UNMAPPED-TR05"


@pytest.mark.asyncio
async def test_upload_applies_equivalence_to_sheet_name_model(
    client, auth_headers, test_users, test_locations, db_session
):
    """TR-05: model taken from the sheet name is also resolved via equivalence."""
    from app.services import model_equivalence_service as me_service

    me_service.upsert_equivalence(db_session, "diaoyu-TR05", "Triciclo Interno Diaoyu")
    content = _make_xlsx([
        ("diaoyu-TR05", [
            ["Frame", "Motor"],
            ["EQ-FRAME-003", "EQ-MOTOR-003"],
        ])
    ])
    resp = await _upload(client, auth_headers, "sheetmodel.xlsx", content)
    assert resp.status_code == 200, resp.text

    unit = db_session.query(Unit).filter(Unit.chassis_number == "EQ-FRAME-003").first()
    assert unit.model == "Triciclo Interno Diaoyu"


# --- TR-06: batch metadata (period/batch + product type) at upload time ------


@pytest.mark.asyncio
async def test_upload_persists_batch_metadata_on_import_and_units(
    client, auth_headers, test_users, test_locations, db_session
):
    """Metadata sent on the form is stored on the import and every unit."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor"],
            ["MD-FRAME-001", "MD-MOTOR-001"],
            ["MD-FRAME-002", "MD-MOTOR-002"],
        ])
    ])
    resp = await _upload(
        client, auth_headers, "meta.xlsx", content,
        data={"batch_period": "2026-ABRIL", "product_type": "triciclo"},
    )
    assert resp.status_code == 200, resp.text
    import_id = resp.json()["import_id"]

    # AC: metadata is returned by GET /imports/{id}
    get_resp = await client.get(f"/api/v1/imports/{import_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    body = get_resp.json()
    assert body["batch_period"] == "2026-ABRIL"
    assert body["product_type"] == "triciclo"

    # AC: metadata is stamped on every created unit
    for frame in ("MD-FRAME-001", "MD-FRAME-002"):
        unit = db_session.query(Unit).filter(Unit.chassis_number == frame).first()
        assert unit.batch_period == "2026-ABRIL"
        assert unit.product_type == "triciclo"


@pytest.mark.asyncio
async def test_upload_without_metadata_is_allowed(
    client, auth_headers, test_users, test_locations, db_session
):
    """Metadata is optional: omitting it stores NULL and does not break import."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor"],
            ["MD-FRAME-003", "MD-MOTOR-003"],
        ])
    ])
    resp = await _upload(client, auth_headers, "nometa.xlsx", content)
    assert resp.status_code == 200, resp.text
    import_id = resp.json()["import_id"]

    get_resp = await client.get(f"/api/v1/imports/{import_id}", headers=auth_headers)
    assert get_resp.json()["batch_period"] is None
    assert get_resp.json()["product_type"] is None

    unit = db_session.query(Unit).filter(Unit.chassis_number == "MD-FRAME-003").first()
    assert unit.batch_period is None
    assert unit.product_type is None


@pytest.mark.asyncio
async def test_upload_blank_metadata_is_normalized_to_null(
    client, auth_headers, test_users, test_locations, db_session
):
    """Whitespace-only metadata is treated as absent (stored as NULL)."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor"],
            ["MD-FRAME-004", "MD-MOTOR-004"],
        ])
    ])
    resp = await _upload(
        client, auth_headers, "blankmeta.xlsx", content,
        data={"batch_period": "   ", "product_type": ""},
    )
    assert resp.status_code == 200, resp.text

    unit = db_session.query(Unit).filter(Unit.chassis_number == "MD-FRAME-004").first()
    assert unit.batch_period is None
    assert unit.product_type is None


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


# --- TR-07: assisted mapping (proposed mapping, manual override, invalid rows) -


async def _preview(client, auth_headers, filename, content, data=None):
    files = {
        "file": (
            filename,
            content,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    return await client.post(
        "/api/v1/imports/preview", files=files, data=data, headers=auth_headers
    )


@pytest.mark.asyncio
async def test_preview_reports_columns_and_proposed_mapping(
    client, auth_headers, test_users, test_locations
):
    """Preview exposes raw columns and a column->field proposal per sheet."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor", "NO"],  # "NO" is not a recognizable synonym
            ["PM-FRAME-001", "PM-MOTOR-001", "X3"],
        ])
    ])
    resp = await _preview(client, auth_headers, "propose.xlsx", content)
    assert resp.status_code == 200, resp.text
    sheet = resp.json()["sheets"][0]
    assert sheet["columns"] == ["Frame", "Motor", "NO"]
    assert sheet["column_mapping"]["Frame"] == "frame"
    assert sheet["column_mapping"]["Motor"] == "motor"
    assert sheet["column_mapping"]["NO"] is None  # unmapped -> proposed as null


@pytest.mark.asyncio
async def test_preview_flags_invalid_rows_without_persisting(
    client, auth_headers, test_users, test_locations, db_session
):
    """Rows with no identifier or duplicate identifiers are flagged; nothing saved."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor", "Color"],
            ["IV-FRAME-001", "IV-MOTOR-001", "Rojo"],
            [None, None, "Verde"],            # no identifier
            ["IV-FRAME-001", "IV-MOTOR-002", "Azul"],  # duplicate frame
        ])
    ])
    resp = await _preview(client, auth_headers, "invalid.xlsx", content)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["invalid_rows_count"] == 2
    reasons = " ".join(r["reasons"][0] for r in body["invalid_rows"])
    assert "No identifier" in reasons
    assert "Duplicate identifier" in reasons
    # Nothing was persisted by the preview.
    assert db_session.query(Unit).filter(Unit.chassis_number == "IV-FRAME-001").first() is None


@pytest.mark.asyncio
async def test_preview_applies_manual_mapping(
    client, auth_headers, test_users, test_locations
):
    """A manual mapping passed to preview re-maps the column in the proposal."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor", "NO"],
            ["PMM-FRAME-001", "PMM-MOTOR-001", "X3"],
        ])
    ])
    resp = await _preview(
        client, auth_headers, "manualpreview.xlsx", content,
        data={"column_mapping": json.dumps({"NO": "model"})},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "model" in body["detected_fields"]
    assert body["sheets"][0]["column_mapping"]["NO"] == "model"
    assert body["preview_data"][0]["model"] == "X3"


@pytest.mark.asyncio
async def test_upload_with_manual_mapping_overrides_detection(
    client, auth_headers, test_users, test_locations, db_session
):
    """A manual mapping on /upload persists the model from an unmapped column."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor", "NO"],
            ["MAP-FRAME-001", "MAP-MOTOR-001", "X3"],
        ])
    ])
    resp = await _upload(
        client, auth_headers, "manual.xlsx", content,
        data={"column_mapping": json.dumps({"NO": "model"})},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["successful_imports"] == 1

    unit = db_session.query(Unit).filter(Unit.chassis_number == "MAP-FRAME-001").first()
    assert unit.model == "X3"  # without the mapping this would be the sheet name


@pytest.mark.asyncio
async def test_upload_rejects_malformed_column_mapping(
    client, auth_headers, test_users, test_locations
):
    """Malformed JSON and unknown fields are rejected with 400 before persisting."""
    content = _make_xlsx([
        ("Sheet1", [
            ["Frame", "Motor"],
            ["BAD-FRAME-001", "BAD-MOTOR-001"],
        ])
    ])
    bad_json = await _upload(
        client, auth_headers, "badjson.xlsx", content,
        data={"column_mapping": "{not json}"},
    )
    assert bad_json.status_code == 400

    bad_field = await _upload(
        client, auth_headers, "badfield.xlsx", content,
        data={"column_mapping": json.dumps({"Frame": "bogus"})},
    )
    assert bad_field.status_code == 400


# --- TR-09: end-to-end import of the real supplier samples + error cases ------

from pathlib import Path  # noqa: E402

_SAMPLES_DIR = Path(__file__).parent / "fixtures" / "samples"
_SAMPLE_MODEL_XLSX = "2025057车 Frame number and motor number.xlsx"
_SAMPLE_ELECTRIC_BIKE_XLSX = "frame number and motor number for electric bike.xlsx"


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_file_type(
    client, auth_headers, test_users, test_locations
):
    """A non-spreadsheet file is rejected with 400 before any processing."""
    resp = await _upload(client, auth_headers, "notes.txt", b"hello world")
    assert resp.status_code == 400
    assert "Invalid file type" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_real_sample_without_identifier_column_fails(
    client, auth_headers, test_users, test_locations
):
    """The header-less sample has no mappable identifier and is reported, not silent."""
    content = (_SAMPLES_DIR / _SAMPLE_ELECTRIC_BIKE_XLSX).read_bytes()
    resp = await _upload(client, auth_headers, _SAMPLE_ELECTRIC_BIKE_XLSX, content)
    assert resp.status_code == 500
    assert "No identifier columns found" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_real_sample_imports_units_and_dedups_shared_motor(
    client, auth_headers, test_users, test_locations, db_session
):
    """End-to-end on the clean English sample.

    The file has 120 unique frames but a placeholder motor ("HUIYOU20250816")
    repeated on 20 rows. Because the importer de-duplicates on either identifier,
    19 of those collide and are reported per-row, leaving 101 units imported.
    This pins the real-data behavior so a future dedup change is a conscious one.
    """
    content = (_SAMPLES_DIR / _SAMPLE_MODEL_XLSX).read_bytes()
    resp = await _upload(client, auth_headers, _SAMPLE_MODEL_XLSX, content)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total_records"] == 120
    assert body["successful_imports"] == 101
    assert body["failed_imports"] == 19

    import_id = body["import_id"]
    errors_resp = await client.get(
        f"/api/v1/imports/{import_id}/errors", headers=auth_headers
    )
    assert errors_resp.status_code == 200
    errors = errors_resp.json()
    assert len(errors) == 19
    assert all("HUIYOU20250816" in e["error_message"] for e in errors)

    # The first row imports cleanly with its model preserved.
    unit = db_session.query(Unit).filter(Unit.chassis_number == "HXY202512001").first()
    assert unit is not None
    assert unit.engine_number == "20260102061514"
    assert unit.model == "X3"
