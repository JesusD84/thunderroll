"""Unit tests for the schema-tolerant import parser (TR-04a).

Focus: header-row detection and the positional fallback. These tests use
in-memory DataFrames so they are fast and need no DB or FastAPI app. Cases are
modeled on the four real supplier samples:
- Sample 1/2: header in row 0 (English headers).
- Sample 3: no header (data starts in row 0) -> positional mapping.
- Sample 4: header with a leading blank column + Chinese/English labels.
"""

import io

import numpy as np
import pandas as pd
import pytest

from app.services.import_parser import (
    WorkbookParseResult,
    apply_manual_mapping,
    detect_header_row,
    excel_engine_for,
    normalize_id_value,
    normalize_label,
    parse_sheet,
    parse_workbook,
    resolve_columns,
    resolve_field,
)


def _df(rows):
    """Build a header-less DataFrame (like pd.read_excel(header=None))."""
    return pd.DataFrame(rows)


def _result_from_df(rows, sheet_name="Sheet1"):
    """Parse one DataFrame into a single-table WorkbookParseResult."""
    table = parse_sheet(_df(rows), sheet_name=sheet_name)
    return WorkbookParseResult(tables=[table])


def test_excel_engine_for():
    assert excel_engine_for("a.xls") == "xlrd"
    assert excel_engine_for("A.XLS") == "xlrd"
    assert excel_engine_for("a.xlsx") == "openpyxl"
    assert excel_engine_for("a.xlsm") == "openpyxl"


def test_detect_header_in_first_row():
    df = _df(
        [
            ["Frame number", "Motor number", "Model"],
            ["HXY202512001", "20260102061514", "X3"],
            ["HXY202512002", "20260102061519", "X3"],
        ]
    )
    assert detect_header_row(df) == 0


def test_detect_header_after_junk_rows():
    df = _df(
        [
            ["Inventario proveedor", None, None],
            [None, None, None],
            ["Frame", "Motor", "Color"],
            ["HXY202603001", "20260417020749", "Red"],
        ]
    )
    assert detect_header_row(df) == 2


def test_detect_header_chinese_labels():
    df = _df(
        [
            [np.nan, "NO", "COLOUR", "电机Motor serial number", "车架号Frame serial number"],
            [1.0, "TY-D530", "红RED", "YC-48V25011431", "341022025020579"],
        ]
    )
    assert detect_header_row(df) == 0


def test_no_header_returns_none():
    # Sample 3: data only, no keyword cells anywhere.
    df = _df(
        [
            ["352222655000228", "ZT48V400W2604S008373", "Blue"],
            ["352222655000149", "ZT48V400W2604S008375", "Blue"],
        ]
    )
    assert detect_header_row(df) is None


def test_parse_sheet_with_header():
    df = _df(
        [
            ["Frame number", "Motor number", "Model"],
            ["HXY202512001", "20260102061514", "X3"],
            [None, None, None],  # blank row should be skipped
            ["HXY202512002", "20260102061519", "X3"],
        ]
    )
    table = parse_sheet(df, sheet_name="Sheet1")

    assert table.has_header is True
    assert table.header_row == 0
    assert table.columns == ["Frame number", "Motor number", "Model"]
    assert len(table.rows) == 2  # blank row skipped
    assert table.rows[0] == {
        "Frame number": "HXY202512001",
        "Motor number": "20260102061514",
        "Model": "X3",
    }
    assert table.issues == []


def test_parse_sheet_without_header_uses_positional():
    df = _df(
        [
            ["352222655000228", "ZT48V400W2604S008373", "Blue"],
            ["352222655000149", "ZT48V400W2604S008375", "Blue"],
        ]
    )
    table = parse_sheet(df, sheet_name="Sheet1")

    assert table.has_header is False
    assert table.header_row is None
    assert table.columns == ["col_0", "col_1", "col_2"]
    assert len(table.rows) == 2
    assert table.rows[0]["col_0"] == "352222655000228"
    # A warning issue is reported when falling back to positional mapping.
    assert any(i.level == "warning" for i in table.issues)


def test_parse_sheet_blank_and_duplicate_header_labels():
    df = _df(
        [
            [np.nan, "Frame", "Frame", "Motor"],
            ["1", "HXY1", "HXY1b", "M1"],
        ]
    )
    table = parse_sheet(df)

    # blank -> positional name; duplicate "Frame" disambiguated.
    assert table.columns == ["col_0", "Frame", "Frame_1", "Motor"]


def test_parse_workbook_csv_with_header():
    content = b"Frame,Motor,Color\nHXY1,M1,Red\nHXY2,M2,Blue\n"
    result = parse_workbook(content, "inventory.csv")

    assert len(result.tables) == 1
    table = result.tables[0]
    assert table.sheet == "csv"
    assert table.has_header is True
    assert table.columns == ["Frame", "Motor", "Color"]
    assert len(table.rows) == 2


def test_parse_workbook_csv_without_header():
    content = b"352222655000228,ZT48V400W2604S008373,Blue\n352222655000149,ZT48,Blue\n"
    result = parse_workbook(content, "inventory.csv")

    table = result.tables[0]
    assert table.has_header is False
    assert table.columns == ["col_0", "col_1", "col_2"]
    assert len(table.rows) == 2


# --- TR-04b: synonym resolution to canonical fields -------------------------


def test_normalize_label_strips_all_whitespace():
    assert normalize_label("Frame number") == "framenumber"
    assert normalize_label("  Motor\nNo. ") == "motorno."
    assert normalize_label("车架号Frame serial number") == "车架号frameserialnumber"
    assert normalize_label(np.nan) == ""


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Frame number", "frame"),
        ("frame number", "frame"),
        ("Frame", "frame"),
        ("车架号Frame serial number", "frame"),
        ("Chassis No.", "frame"),
        ("Motor number", "motor"),
        ("Motor", "motor"),
        ("电机Motor serial number", "motor"),
        ("Engine No", "motor"),
        ("Color", "color"),
        ("COLOUR", "color"),
        ("颜色", "color"),
        ("Model", "model"),
        ("型号", "model"),
        # Unknown / ambiguous labels resolve to None.
        ("NO", None),
        ("Observaciones", None),
        ("", None),
    ],
)
def test_resolve_field(label, expected):
    assert resolve_field(label) == expected


def test_resolve_columns_duplicate_field_keeps_first_and_warns():
    field_map, issues = resolve_columns(["Frame number", "Frame", "Color"])
    assert field_map == {"frame": "Frame number", "color": "Color"}
    assert any(i.level == "warning" and "frame" in i.message for i in issues)


def test_field_map_sample1_headers():
    df = _df(
        [
            ["Frame number", "Motor number", "Model"],
            ["HXY202512001", "20260102061514", "X3"],
        ]
    )
    table = parse_sheet(df, sheet_name="Sheet1")
    assert table.field_map == {
        "frame": "Frame number",
        "motor": "Motor number",
        "model": "Model",
    }


def test_field_map_sample2_with_junk_column():
    # tricycle.xls sheets: Frame | Motor | Color | <junk col with nan header>
    df = _df(
        [
            ["Frame ", "Motor", "Color", np.nan],
            ["HXY202603001", "20260417020749", "Red", "legend"],
        ]
    )
    table = parse_sheet(df, sheet_name="X3")
    assert table.field_map == {
        "frame": "Frame",
        "motor": "Motor",
        "color": "Color",
    }
    # the junk 4th column is left unmapped
    assert "col_3" in table.columns


def test_field_map_sample4_chinese_headers():
    df = _df(
        [
            [np.nan, "NO", "COLOUR", "电机Motor serial number", "车架号Frame serial number"],
            [1.0, "TY-D530", "红RED", "YC-48V25011431", "341022025020579"],
        ]
    )
    table = parse_sheet(df, sheet_name="Sheet1")
    assert table.field_map == {
        "color": "COLOUR",
        "motor": "电机Motor serial number",
        "frame": "车架号Frame serial number",
    }
    # 'NO' (model column in the file) is not a recognized synonym -> unmapped.
    assert "model" not in table.field_map


def test_field_map_sample3_no_header_is_empty():
    df = _df(
        [
            ["352222655000228", "ZT48V400W2604S008373", "Blue"],
            ["352222655000149", "ZT48V400W2604S008375", "Blue"],
        ]
    )
    table = parse_sheet(df, sheet_name="Sheet1")
    assert table.has_header is False
    assert table.field_map == {}


# --- TR-04c: read every sheet that contains data ----------------------------


def _xlsx_bytes(sheets: dict) -> bytes:
    """Build an in-memory .xlsx where each row of the input becomes a sheet row.

    Each value is a list of rows (lists). The first row is treated as the
    supplier header, mirroring the real sample layout.
    """
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, index=False, header=False)
    return buf.getvalue()


def test_parse_workbook_multisheet_counts_and_origin():
    # Mirrors tricycle.xls: three data sheets, each named like a model.
    content = _xlsx_bytes(
        {
            "X3": [["Frame", "Motor", "Color"], ["F1", "M1", "Red"], ["F2", "M2", "Black"]],
            "xiaodou": [["Frame", "Motor", "Color"], ["F3", "M3", "Grey"]],
            "diaoyu": [["frame number", "motor number", "Color"], ["F4", "M4", "Blue"]],
        }
    )
    result = parse_workbook(content, "tricycle.xlsx")

    assert [t.sheet for t in result.tables] == ["X3", "xiaodou", "diaoyu"]
    assert [len(t.rows) for t in result.tables] == [2, 1, 1]
    # Origin (sheet name) is preserved and headers resolved per sheet.
    for table in result.tables:
        assert table.field_map == {"frame": table.columns[0], "motor": table.columns[1], "color": "Color"}


def test_parse_workbook_skips_empty_and_header_only_sheets():
    content = _xlsx_bytes(
        {
            "Data": [["Frame", "Motor", "Color"], ["F1", "M1", "Red"]],
            "Empty": [],  # truly empty sheet
            "HeaderOnly": [["Frame", "Motor", "Color"]],  # header, no data rows
        }
    )
    result = parse_workbook(content, "wb.xlsx")

    assert [t.sheet for t in result.tables] == ["Data"]
    skipped = {i.sheet: i.message for i in result.issues if i.level == "info"}
    assert "Empty" in skipped
    assert "HeaderOnly" in skipped
    assert "no data rows" in skipped["HeaderOnly"]


def test_iter_rows_flattens_across_sheets_with_origin():
    content = _xlsx_bytes(
        {
            "X3": [["Frame", "Motor", "Color"], ["F1", "M1", "Red"], ["F2", "M2", "Black"]],
            "xiaodou": [["Frame", "Motor", "Color"], ["F3", "M3", "Grey"]],
        }
    )
    result = parse_workbook(content, "tricycle.xlsx")

    rows = list(result.iter_rows())
    assert len(rows) == 3
    assert [r.sheet for r in rows] == ["X3", "X3", "xiaodou"]
    # canonical() maps to frame/motor/color regardless of sheet.
    assert rows[0].canonical() == {"frame": "F1", "motor": "M1", "color": "Red"}
    assert rows[2].canonical() == {"frame": "F3", "motor": "M3", "color": "Grey"}


# --- TR-04d: frame/motor type normalization ---------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        # 15-digit number stored as int / float must stay a 15-digit string.
        (352222655000228, "352222655000228"),
        (352222655000228.0, "352222655000228"),
        (np.int64(341022025020579), "341022025020579"),
        (np.float64(341022025020579.0), "341022025020579"),
        # Alphanumeric motors (Samples 3/4) kept verbatim.
        ("ZT48V400W2604S008373", "ZT48V400W2604S008373"),
        ("YC-48V25011431", "YC-48V25011431"),
        # Existing strings: trimmed, leading zeros preserved.
        ("  HXY202512001 ", "HXY202512001"),
        ("00123", "00123"),
        # Blank / NaN -> empty string.
        (np.nan, ""),
        (None, ""),
        # Non-integral float keeps its fractional part without trailing zeros.
        (12.5, "12.5"),
    ],
)
def test_normalize_id_value(value, expected):
    assert normalize_id_value(value) == expected


def test_normalize_id_value_no_scientific_notation():
    # A large float must never render in scientific notation.
    result = normalize_id_value(3.52222655000228e14)
    assert "e" not in result.lower()
    assert result == "352222655000228"


def test_canonical_normalizes_only_frame_and_motor():
    df = _df(
        [
            ["Frame", "Motor", "Color"],
            [352222655000228, 20260102061514, "Blue"],
        ]
    )
    table = parse_sheet(df, sheet_name="Sheet1")
    from app.services.import_parser import SheetRow

    sr = SheetRow(
        sheet=table.sheet,
        has_header=table.has_header,
        field_map=table.field_map,
        values=table.rows[0],
    )
    canonical = sr.canonical()
    # frame/motor -> exact strings; color untouched.
    assert canonical["frame"] == "352222655000228"
    assert canonical["motor"] == "20260102061514"
    assert canonical["color"] == "Blue"


def test_numeric_frame_via_workbook_roundtrip_stays_string():
    # Frame stored as a number in the .xlsx must come out as a clean string.
    content = _xlsx_bytes(
        {
            "Sheet1": [
                ["Frame", "Motor", "Color"],
                [352222655000228, "ZT48V400W2604S008373", "Blue"],
            ]
        }
    )
    result = parse_workbook(content, "wb.xlsx")
    canonical = next(result.iter_rows()).canonical()
    assert canonical["frame"] == "352222655000228"
    assert "." not in canonical["frame"]
    assert canonical["motor"] == "ZT48V400W2604S008373"


# --- TR-04e: junk columns and merged-cell forward-fill ----------------------


def test_forward_fill_merged_model_column():
    # Model is a merged cell: only the first row of each block carries it.
    df = _df(
        [
            ["Frame", "Motor", "Model"],
            ["F1", "M1", "X3"],
            ["F2", "M2", None],
            ["F3", "M3", None],
            ["F4", "M4", "Y5"],
        ]
    )
    table = parse_sheet(df, sheet_name="Sheet1")
    models = [r["Model"] for r in table.rows]
    assert models == ["X3", "X3", "X3", "Y5"]
    assert any(
        i.level == "info" and "Forward-filled" in i.message and "model" in i.message
        for i in table.issues
    )


def test_identifier_columns_are_never_forward_filled():
    # A blank frame must stay blank, not inherit the row above.
    df = _df(
        [
            ["Frame", "Motor", "Color"],
            ["F1", "M1", "Red"],
            [None, "M2", "Blue"],
        ]
    )
    table = parse_sheet(df, sheet_name="Sheet1")
    # raw second row frame is blank, not "F1"
    assert table.rows[1]["Frame"] != "F1"
    # and through canonical(), the blank frame normalizes to "" (not "F1")
    from app.services.import_parser import SheetRow

    sr = SheetRow(table.sheet, table.has_header, table.field_map, table.rows[1])
    assert sr.canonical()["frame"] == ""


def test_color_legend_column_is_ignored():
    # Mirrors Sample 2: a 4th column holds a colour legend only in the 1st row.
    df = _df(
        [
            ["Frame", "Motor", "Color", None],
            ["F1", "M1", "Red", "Red9  Blue5  Black6 Grey4"],
            ["F2", "M2", "Black", None],
        ]
    )
    table = parse_sheet(df, sheet_name="X3")
    assert "col_3" not in table.field_map.values()
    assert any(
        i.level == "info" and "Ignoring" in i.message and "col_3" in i.message
        for i in table.issues
    )
    from app.services.import_parser import SheetRow

    sr = SheetRow(table.sheet, table.has_header, table.field_map, table.rows[0])
    # the legend text never appears in the canonical unit row
    assert sr.canonical() == {"frame": "F1", "motor": "M1", "color": "Red"}


def test_missing_optional_fields_do_not_break_parsing():
    df = _df(
        [
            ["Frame number", "Motor number"],
            ["F1", "M1"],
        ]
    )
    table = parse_sheet(df, sheet_name="Sheet1")
    assert table.field_map == {"frame": "Frame number", "motor": "Motor number"}
    from app.services.import_parser import SheetRow

    sr = SheetRow(table.sheet, table.has_header, table.field_map, table.rows[0])
    assert sr.canonical() == {"frame": "F1", "motor": "M1"}


# --- TR-07: manual mapping override ------------------------------------------


def test_apply_manual_mapping_maps_unrecognized_column_to_model():
    # Sample-4 shape: the model lives under a "NO" column the parser can't resolve.
    result = _result_from_df([
        ["Frame", "Motor", "NO"],
        ["F1", "M1", "X3"],
        ["F2", "M2", "xiaodou"],
    ])
    table = result.tables[0]
    assert "model" not in table.field_map  # not auto-detected

    apply_manual_mapping(result, {"NO": "model"})

    assert table.field_map["model"] == "NO"
    rows = [r for r in result.iter_rows()]
    assert rows[0].canonical()["model"] == "X3"
    assert rows[1].canonical()["model"] == "xiaodou"


def test_apply_manual_mapping_forward_fills_merged_model_column():
    result = _result_from_df([
        ["Frame", "Motor", "NO"],
        ["F1", "M1", "X3"],
        ["F2", "M2", None],  # merged cell under the manually mapped model column
        ["F3", "M3", None],
    ])
    apply_manual_mapping(result, {"NO": "model"})
    models = [r.canonical()["model"] for r in result.iter_rows()]
    assert models == ["X3", "X3", "X3"]


def test_apply_manual_mapping_reassigns_a_column_to_one_field():
    result = _result_from_df([
        ["Frame", "Motor"],
        ["F1", "M1"],
    ])
    # Reassign the auto-detected frame column to model; it must not stay as frame.
    apply_manual_mapping(result, {"Frame": "model"})
    fm = result.tables[0].field_map
    assert fm.get("model") == "Frame"
    assert fm.get("frame") != "Frame"


def test_apply_manual_mapping_ignores_unknown_field_and_missing_column():
    result = _result_from_df([
        ["Frame", "Motor"],
        ["F1", "M1"],
    ])
    before = dict(result.tables[0].field_map)
    apply_manual_mapping(result, {"Motor": "bogus", "DoesNotExist": "model"})
    assert result.tables[0].field_map == before
