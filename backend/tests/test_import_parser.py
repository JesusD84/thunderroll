"""Unit tests for the schema-tolerant import parser (TR-04a).

Focus: header-row detection and the positional fallback. These tests use
in-memory DataFrames so they are fast and need no DB or FastAPI app. Cases are
modeled on the four real supplier samples:
- Sample 1/2: header in row 0 (English headers).
- Sample 3: no header (data starts in row 0) -> positional mapping.
- Sample 4: header with a leading blank column + Chinese/English labels.
"""

import numpy as np
import pandas as pd

from app.services.import_parser import (
    detect_header_row,
    excel_engine_for,
    parse_sheet,
    parse_workbook,
)


def _df(rows):
    """Build a header-less DataFrame (like pd.read_excel(header=None))."""
    return pd.DataFrame(rows)


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
