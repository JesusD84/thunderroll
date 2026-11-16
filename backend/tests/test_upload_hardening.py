"""Regression tests for the upload hardening.

Covers the guarantees the import endpoints must keep:

- A filename crafted for path traversal is stored safely (server-generated
  name, inside the storage directory, nothing written outside it).
- An oversized file is rejected with 413 instead of being loaded whole.
- A CSV written by a Spanish Excel (cp1252, ``;`` separator) is processed
  correctly, and a UTF-8 BOM does not corrupt the first header.
- The uploads directory is not served by the API.
- An unexpected failure returns a generic message, never the raw exception.
"""

import io
import uuid

import pytest
from httpx import AsyncClient
from openpyxl import Workbook

from app.models.models import Import, Unit


@pytest.fixture(autouse=True)
def storage_dir(tmp_path, monkeypatch):
    """Point the upload storage at a temporary directory.

    The backend reads the variable on every call, so the tests never write to
    the real storage directory.
    """
    target = tmp_path / "imports"
    monkeypatch.setenv("IMPORT_STORAGE_DIR", str(target))
    return target


def _make_xlsx(sheets: list[tuple[str, list[list]]]) -> bytes:
    """Build an in-memory .xlsx from ``[(sheet_name, rows), ...]``."""
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
    files = {"file": (filename, content, "application/octet-stream")}
    return await client.post(
        "/api/v1/imports/upload", files=files, data=data, headers=auth_headers
    )


# ---------------------------------------------------------------------------
# 1. Path traversal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_traversal_filename_is_stored_safely(
    client: AsyncClient,
    auth_headers,
    storage_dir,
    db_session,
):
    """A traversal filename never escapes the storage directory."""
    content = _make_xlsx(
        [("Sheet1", [["Frame", "Motor"], ["TRV-FRAME-001", "TRV-MOTOR-001"]])]
    )

    resp = await _upload(client, auth_headers, "../../../etc/passwd.xlsx", content)
    assert resp.status_code == 200, resp.text

    # Exactly one file, and it lives inside the storage directory.
    stored = list(storage_dir.iterdir())
    assert len(stored) == 1
    assert stored[0].parent == storage_dir

    # The name is server-generated: uuid4 + the validated extension.
    assert stored[0].suffix == ".xlsx"
    assert uuid.UUID(stored[0].stem)  # raises if it is not a uuid

    # Nothing was written next to (or above) the storage directory.
    assert not (storage_dir.parent / "etc").exists()
    assert not (storage_dir.parent / "passwd.xlsx").exists()

    # The record keeps the original name as metadata, without any path.
    import_id = resp.json()["import_id"]
    record = db_session.query(Import).filter(Import.id == import_id).first()
    assert record is not None
    assert record.original_filename == "passwd.xlsx"
    assert "/" not in record.original_filename
    assert "\\" not in record.original_filename
    # The stored name is a bare file name, not a path.
    assert "/" not in record.filename
    assert record.filename == stored[0].name


@pytest.mark.asyncio
async def test_api_never_returns_the_server_storage_path(
    client: AsyncClient, auth_headers, storage_dir
):
    """The storage location is not exposed by the API."""
    content = _make_xlsx(
        [("Sheet1", [["Frame", "Motor"], ["LEAK-FRAME-001", "LEAK-MOTOR-001"]])]
    )
    resp = await _upload(client, auth_headers, "inventario.xlsx", content)
    assert resp.status_code == 200, resp.text
    assert str(storage_dir) not in resp.text

    listing = await client.get("/api/v1/imports/", headers=auth_headers)
    assert listing.status_code == 200
    body = listing.text
    assert str(storage_dir) not in body
    assert "var/imports" not in body

    import_id = resp.json()["import_id"]
    detail = await client.get(f"/api/v1/imports/{import_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert str(storage_dir) not in detail.text
    # The `filename` field shows the original name, not the stored one.
    assert detail.json()["filename"] == "inventario.xlsx"


# ---------------------------------------------------------------------------
# 2. Límites
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_oversized_file_is_rejected_with_413(
    client: AsyncClient, auth_headers, storage_dir, monkeypatch
):
    """A file over the size limit is cut off while it is being read."""
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "1")

    # 1 MiB + 1 KiB: just over the 1 MB limit configured above.
    payload = b"0" * (1024 * 1024 + 1024)
    resp = await _upload(client, auth_headers, "grande.xlsx", payload)

    assert resp.status_code == 413
    detail = resp.json()["detail"]
    assert "tamaño máximo" in detail.lower()
    assert "1 MB" in detail

    # The oversized file was not left on disk.
    assert not storage_dir.exists() or not list(storage_dir.iterdir())


@pytest.mark.asyncio
async def test_file_over_the_row_limit_is_rejected_with_422(
    client: AsyncClient, auth_headers, storage_dir, monkeypatch
):
    """A sheet with more rows than allowed is rejected with 422."""
    monkeypatch.setenv("MAX_IMPORT_ROWS_PER_SHEET", "5")

    rows = [["Frame", "Motor"]] + [[f"ROW-{i}", f"MOT-{i}"] for i in range(20)]
    content = _make_xlsx([("Sheet1", rows)])

    resp = await _upload(client, auth_headers, "muchas_filas.xlsx", content)
    assert resp.status_code == 422
    assert "filas" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_rows_beyond_the_limit_are_never_dropped_silently(
    client: AsyncClient, auth_headers, storage_dir, monkeypatch, db_session
):
    """A file that does not fit is rejected, never imported truncated.

    The blank rows used to shift the count: the sheet was read up to the cap,
    the blank row made the visible count fit the limit, and the units after
    it were imported nowhere without a word.
    """
    monkeypatch.setenv("MAX_IMPORT_ROWS_PER_SHEET", "5")

    rows = (
        [["Frame", "Motor"]]
        + [[f"BLANK-F-{i}", f"BLANK-M-{i}"] for i in range(5)]
        + [[None, None]]  # a blank row shifts the count
        + [[f"LATE-F-{i}", f"LATE-M-{i}"] for i in range(3)]  # would be lost
    )
    content = _make_xlsx([("Sheet1", rows)])

    resp = await _upload(client, auth_headers, "con_huecos.xlsx", content)
    assert resp.status_code == 422
    assert "filas" in resp.json()["detail"].lower()

    # Nothing was imported: a truncated import is worse than no import.
    leaked = db_session.query(Unit).filter(Unit.chassis_number.like("LATE-F-%")).count()
    assert leaked == 0


@pytest.mark.asyncio
async def test_file_with_too_many_sheets_is_rejected_with_422(
    client: AsyncClient, auth_headers, storage_dir, monkeypatch
):
    """A workbook with more sheets than allowed is rejected with 422."""
    monkeypatch.setenv("MAX_IMPORT_SHEETS", "2")

    content = _make_xlsx(
        [
            (f"Hoja{i}", [["Frame", "Motor"], [f"S{i}-FRAME", f"S{i}-MOTOR"]])
            for i in range(5)
        ]
    )

    resp = await _upload(client, auth_headers, "muchas_hojas.xlsx", content)
    assert resp.status_code == 422
    assert "hojas" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 3. Codificación de los CSV
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cp1252_csv_with_accents_is_processed(
    client: AsyncClient, auth_headers, storage_dir, db_session
):
    """A CSV saved by a Spanish Excel (cp1252, ';') is imported correctly."""
    text = (
        "Chasis;Motor;Color;Modelo\n"
        "CP1252-CH-001;CP1252-MO-001;Azul;X3 Ñandú\n"
        "CP1252-CH-002;CP1252-MO-002;Negro;TY-D530\n"
    )
    content = text.encode("cp1252")

    resp = await _upload(client, auth_headers, "inventario.csv", content)
    assert resp.status_code == 200, resp.text
    assert resp.json()["successful_imports"] == 2

    unit = db_session.query(Unit).filter(Unit.chassis_number == "CP1252-CH-001").first()
    assert unit is not None
    assert unit.engine_number == "CP1252-MO-001"
    assert unit.color == "Azul"
    assert unit.model == "X3 Ñandú"


@pytest.mark.asyncio
async def test_utf8_bom_does_not_corrupt_the_first_header(
    client: AsyncClient, auth_headers, storage_dir, db_session
):
    """A UTF-8 BOM does not break the detection of the first column."""
    text = "Chasis,Motor,Color\nBOM-CH-001,BOM-MO-001,Rojo\n"
    content = text.encode("utf-8-sig")

    resp = await _upload(client, auth_headers, "bom.csv", content)
    assert resp.status_code == 200, resp.text
    assert resp.json()["successful_imports"] == 1

    unit = db_session.query(Unit).filter(Unit.chassis_number == "BOM-CH-001").first()
    assert unit is not None
    assert unit.engine_number == "BOM-MO-001"


# ---------------------------------------------------------------------------
# 4. El directorio de uploads no se sirve
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_uploads_path_is_not_served(client: AsyncClient):
    """Nothing under /uploads is reachable through the API."""
    from app.main import app

    assert not any(getattr(route, "path", "") == "/uploads" for route in app.routes)

    for path in ("/uploads/", "/uploads/inventario.xlsx", "/uploads/anything"):
        resp = await client.get(path)
        assert resp.status_code == 404, path


# ---------------------------------------------------------------------------
# 5. Errores inesperados
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unexpected_error_returns_a_generic_message(
    client: AsyncClient, auth_headers, storage_dir, monkeypatch, db_session
):
    """An unexpected failure returns a generic message, not the raw exception."""

    def boom(*args, **kwargs):
        raise RuntimeError("detalle interno que no debe salir")

    monkeypatch.setattr(
        "app.api.v1.endpoints.imports.parse_workbook",
        boom,
    )

    content = _make_xlsx(
        [("Sheet1", [["Frame", "Motor"], ["BOOM-FRAME-001", "BOOM-MOTOR-001"]])]
    )
    resp = await _upload(client, auth_headers, "boom.xlsx", content)

    assert resp.status_code == 500
    detail = resp.json()["detail"]
    assert "detalle interno que no debe salir" not in detail
    assert "boom" not in detail.lower()
    # The user gets a reference to quote when reporting the problem.
    assert "referencia" in detail.lower()

    # The failed import is recorded, without leaking the exception either.
    record = (
        db_session.query(Import).filter(Import.original_filename == "boom.xlsx").first()
    )
    assert record is not None
    assert record.status == "failed"
    assert "detalle interno que no debe salir" not in (record.notes or "")


@pytest.mark.asyncio
async def test_validation_errors_do_not_leak_internals(
    client: AsyncClient, auth_headers, storage_dir
):
    """A file without identifier columns answers 422 with a readable message."""
    content = _make_xlsx([("Sheet1", [["Color", "Model"], ["Rojo", "X3"]])])

    resp = await _upload(client, auth_headers, "sin_id.xlsx", content)
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "identificador" in detail.lower()
    assert "Traceback" not in detail
    assert "Error processing file" not in detail
