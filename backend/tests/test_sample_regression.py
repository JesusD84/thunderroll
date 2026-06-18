"""Regression tests for the import parser against the four real supplier files
(TR-09).

Each sample exercises a distinct edge case that broke the original importer:

- ``2025057车 Frame number and motor number.xlsx`` -> clean English header with a
  ``Model`` column; two trailing empty sheets that must be skipped.
- ``Frame number for tricycle .xls`` -> legacy ``.xls`` (xlrd) with three data
  sheets and a per-sheet color-legend junk column.
- ``frame number and motor number for electric bike.xlsx`` -> no header row, so
  columns can only be mapped positionally (needs assisted mapping, TR-07).
- ``jc  电机车架号.xl.xlsx`` -> Chinese/English headers, a leading index column,
  the model hidden under a non-synonym ``NO`` column (merged cells), and a
  15-digit numeric frame that must survive as an exact string.

The fixtures live in ``tests/fixtures/samples`` and are versioned so these run
in CI (Docker) with no external dependencies.
"""

from pathlib import Path

import pytest

from app.services.import_parser import apply_manual_mapping, parse_workbook

SAMPLES_DIR = Path(__file__).parent / "fixtures" / "samples"

SAMPLE_MODEL_XLSX = "2025057车 Frame number and motor number.xlsx"
SAMPLE_TRICYCLE_XLS = "Frame number for tricycle .xls"
SAMPLE_ELECTRIC_BIKE_XLSX = "frame number and motor number for electric bike.xlsx"
SAMPLE_CHINESE_XLSX = "jc  电机车架号.xl.xlsx"

ALL_SAMPLES = [
    SAMPLE_MODEL_XLSX,
    SAMPLE_TRICYCLE_XLS,
    SAMPLE_ELECTRIC_BIKE_XLSX,
    SAMPLE_CHINESE_XLSX,
]


def _parse(name: str):
    return parse_workbook((SAMPLES_DIR / name).read_bytes(), name)


def _unit_counts_by_sheet(result) -> dict:
    """Count rows that resolve to a unit (have a frame or motor) per sheet."""
    counts: dict = {}
    for sr in result.iter_rows():
        c = sr.canonical()
        if (c.get("frame") or "").strip() or (c.get("motor") or "").strip():
            counts[sr.sheet] = counts.get(sr.sheet, 0) + 1
    return counts


@pytest.mark.parametrize("name", ALL_SAMPLES)
def test_sample_fixture_is_versioned_and_parses(name):
    """Every sample is committed and the parser never raises on it."""
    assert (SAMPLES_DIR / name).is_file()
    result = _parse(name)
    assert result.tables is not None


def test_sample_with_model_column():
    """English header + Model column; trailing empty sheets are skipped."""
    result = _parse(SAMPLE_MODEL_XLSX)
    assert [t.sheet for t in result.tables] == ["Sheet1"]

    table = result.tables[0]
    assert table.has_header is True
    assert table.field_map == {
        "frame": "Frame number",
        "motor": "Motor number",
        "model": "Model",
    }
    assert _unit_counts_by_sheet(result) == {"Sheet1": 120}

    first = next(result.iter_rows()).canonical()
    assert first["frame"] == "HXY202512001"
    assert first["motor"] == "20260102061514"
    assert first["model"] == "X3"

    # The two extra empty sheets are reported as skipped, not parsed.
    skipped = [i.message for i in result.issues if "empty" in i.message.lower()]
    assert len(skipped) == 2


def test_sample_tricycle_multisheet_xls():
    """Legacy .xls with three data sheets and a color-legend junk column."""
    result = _parse(SAMPLE_TRICYCLE_XLS)

    counts = _unit_counts_by_sheet(result)
    assert counts == {"X3": 24, "xiaodou": 24, "diaoyu": 36}
    assert sum(counts.values()) == 84

    # Each sheet maps frame + motor + color (headers differ in case/wording).
    for table in result.tables:
        assert {"frame", "motor", "color"} <= set(table.field_map)

    # The trailing color-legend column (col_3) is recognized as junk and ignored.
    assert any("col_3" in i.message for i in result.issues if "Ignoring" in i.message)

    x3_first = next(sr for sr in result.iter_rows() if sr.sheet == "X3").canonical()
    assert x3_first["frame"] == "HXY202603001"
    assert x3_first["motor"] == "20260417020749"
    assert x3_first["color"] == "Red"


def test_sample_electric_bike_has_no_header():
    """No header row: columns are positional, so nothing auto-maps (needs TR-07)."""
    result = _parse(SAMPLE_ELECTRIC_BIKE_XLSX)
    assert [t.sheet for t in result.tables] == ["Sheet1"]

    table = result.tables[0]
    assert table.has_header is False
    # Positional columns (col_0..) have no synonyms -> empty auto-mapping.
    assert table.field_map == {}
    # The data rows are still read; they just await a manual mapping.
    assert len(table.rows) == 35
    assert any(
        i.level == "warning" and "no header" in i.message.lower()
        for i in result.issues
    )


def test_sample_electric_bike_recovers_with_manual_mapping():
    """A positional file becomes importable once the user maps columns (TR-07)."""
    result = _parse(SAMPLE_ELECTRIC_BIKE_XLSX)
    # The first three positional columns are frame, motor and color.
    apply_manual_mapping(result, {"col_0": "frame", "col_1": "motor", "col_2": "color"})
    assert result.tables[0].field_map == {
        "frame": "col_0",
        "motor": "col_1",
        "color": "col_2",
    }
    assert _unit_counts_by_sheet(result) == {"Sheet1": 35}


def test_sample_chinese_headers_and_numeric_frame_preserved():
    """Chinese/English headers, index + NO junk columns, 15-digit numeric frame."""
    result = _parse(SAMPLE_CHINESE_XLSX)
    assert [t.sheet for t in result.tables] == ["Sheet1"]

    table = result.tables[0]
    assert table.field_map == {
        "color": "COLOUR",
        "motor": "电机Motor serial number",
        "frame": "车架号Frame serial number",
    }
    # The model lives under a non-synonym "NO" column, so it is not auto-mapped.
    assert "model" not in table.field_map
    # The leading index column (col_0) and NO are reported as ignored.
    assert any(
        "col_0" in i.message and "NO" in i.message for i in result.issues
    )
    assert _unit_counts_by_sheet(result) == {"Sheet1": 98}

    first = next(result.iter_rows()).canonical()
    # A 15-digit numeric frame must survive as an exact string (no sci-notation
    # / no trailing .0 / no truncation).
    assert first["frame"] == "341022025020579"
    assert first["frame"].isdigit() and len(first["frame"]) == 15
    assert "e" not in first["frame"].lower() and "." not in first["frame"]
    # Alphanumeric motor kept intact.
    assert first["motor"] == "YC-48V25011431"
    assert first["color"] == "红RED"


def test_sample_chinese_model_recovered_from_merged_no_column():
    """Mapping the NO column to model forward-fills the merged model values."""
    result = _parse(SAMPLE_CHINESE_XLSX)
    apply_manual_mapping(result, {"NO": "model"})
    assert result.tables[0].field_map["model"] == "NO"

    models = [sr.canonical().get("model") for sr in result.iter_rows()]
    # Forward-fill leaves no gaps: every unit inherits its block's model.
    assert all(m for m in models)
    # The first block is "TY-D530"; the file has several model blocks.
    assert models[0] == "TY-D530"
    assert "TY-D530" in models and len(set(models)) > 1
