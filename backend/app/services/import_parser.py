"""Schema-tolerant parser for supplier inventory files.

This module is the single entry point for turning a heterogeneous supplier
spreadsheet into normalized rows plus an issues report. Suppliers send wildly
different layouts (English/Chinese headers, files with no header row, multiple
sheets, junk columns, merged cells), so the parser is built incrementally:

- TR-04a (this file): skeleton + header-row detection + positional fallback.
- TR-04b: multilingual synonym dictionary -> canonical fields.
- TR-04c: read every sheet that contains data.
- TR-04d: type normalization for frame/motor numbers.
- TR-04e: junk-column and merged-cell cleanup.

The public surface is intentionally dependency-light (pandas + stdlib only) so
it can be unit-tested without standing up the FastAPI app.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any, Optional, Union

import pandas as pd

# Source can be a filesystem path or the raw bytes of an uploaded file.
Source = Union[str, bytes]

# Minimal keyword set used only to tell a header row apart from a data row.
# The full multilingual synonym -> canonical-field mapping lands in TR-04b;
# here we just need enough signal to locate (or rule out) a header row.
HEADER_KEYWORDS: tuple[str, ...] = (
    "frame",
    "chassis",
    "chasis",
    "motor",
    "engine",
    "color",
    "colour",
    "model",
    "modelo",
    "marca",
    "brand",
    # Chinese
    "车架",  # frame
    "电机",  # motor
    "颜色",  # color
    "型号",  # model
)

# A row needs at least this many header-keyword hits to be considered a header.
_MIN_HEADER_MATCHES = 2
# How many leading rows to scan when looking for a header.
_MAX_HEADER_SCAN = 10


@dataclass
class ParseIssue:
    """A single non-fatal problem found while parsing."""

    level: str  # "info" | "warning" | "error"
    message: str
    sheet: Optional[str] = None
    row: Optional[int] = None


@dataclass
class ParsedTable:
    """Result of parsing one sheet.

    ``rows`` are dicts keyed by the (normalized) header label when a header was
    detected, or by positional names (``col_0``, ``col_1`` ...) otherwise. Cell
    values are returned as-is; type normalization is TR-04d.
    """

    sheet: Optional[str]
    has_header: bool
    header_row: Optional[int]
    columns: list[str]
    rows: list[dict[str, Any]]
    issues: list[ParseIssue] = field(default_factory=list)


@dataclass
class WorkbookParseResult:
    """Aggregate result for a whole file (one entry per non-empty sheet)."""

    tables: list[ParsedTable] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)


def excel_engine_for(filename: str) -> str:
    """Return the explicit pandas engine for an Excel filename.

    Legacy ``.xls`` files require ``xlrd``; modern ``.xlsx``/``.xlsm`` files use
    ``openpyxl``. Selecting the engine explicitly avoids relying on pandas'
    auto-detection and makes the ``.xls`` dependency a hard, visible requirement.
    """
    if filename.lower().endswith(".xls"):
        return "xlrd"
    return "openpyxl"


def _is_blank(value: Any) -> bool:
    """True for None, NaN, or whitespace-only / 'nan' string cells."""
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() == "nan"


def _norm_label(value: Any) -> str:
    """Normalize a header label: collapse newlines/whitespace, strip."""
    if _is_blank(value):
        return ""
    return " ".join(str(value).split())


def _looks_like_header_cell(value: Any) -> bool:
    """True if the cell text contains a known header keyword."""
    if _is_blank(value):
        return False
    text = str(value).strip().lower()
    return any(keyword in text for keyword in HEADER_KEYWORDS)


def detect_header_row(
    raw: pd.DataFrame, max_scan: int = _MAX_HEADER_SCAN
) -> Optional[int]:
    """Heuristically locate the header row in a header-less DataFrame.

    The DataFrame must be read with ``header=None`` so every spreadsheet row is
    a data row. We scan the first ``max_scan`` rows and return the index of the
    first row whose cells contain at least ``_MIN_HEADER_MATCHES`` header
    keywords. Returns ``None`` when no such row exists (e.g. a file that has no
    header at all and must be mapped positionally).
    """
    scan = min(max_scan, len(raw))
    for i in range(scan):
        row = raw.iloc[i].tolist()
        matches = sum(1 for cell in row if _looks_like_header_cell(cell))
        if matches >= _MIN_HEADER_MATCHES:
            return i
    return None


def _column_names(header_values: Optional[list[Any]], width: int) -> list[str]:
    """Build column names from a header row, falling back to positional names.

    Blank/duplicate header labels are replaced/disambiguated with positional
    names so downstream code always has a stable, unique key per column.
    """
    names: list[str] = []
    seen: dict[str, int] = {}
    for idx in range(width):
        label = ""
        if header_values is not None and idx < len(header_values):
            label = _norm_label(header_values[idx])
        if not label:
            label = f"col_{idx}"
        if label in seen:
            seen[label] += 1
            label = f"{label}_{seen[label]}"
        else:
            seen[label] = 0
        names.append(label)
    return names


def parse_sheet(raw: pd.DataFrame, sheet_name: Optional[str] = None) -> ParsedTable:
    """Parse a single raw sheet (read with ``header=None``) into a ParsedTable."""
    issues: list[ParseIssue] = []
    width = raw.shape[1]

    header_row = detect_header_row(raw)
    has_header = header_row is not None

    if has_header:
        header_values = raw.iloc[header_row].tolist()
        columns = _column_names(header_values, width)
        data = raw.iloc[header_row + 1 :]
    else:
        columns = _column_names(None, width)
        data = raw
        issues.append(
            ParseIssue(
                level="warning",
                message=(
                    "No header row detected; mapping columns by position "
                    f"({', '.join(columns)})."
                ),
                sheet=sheet_name,
            )
        )

    rows: list[dict[str, Any]] = []
    for _, series in data.iterrows():
        values = series.tolist()
        if all(_is_blank(v) for v in values):
            continue  # skip fully-empty rows
        rows.append({columns[i]: values[i] for i in range(width)})

    return ParsedTable(
        sheet=sheet_name,
        has_header=has_header,
        header_row=header_row,
        columns=columns,
        rows=rows,
        issues=issues,
    )


def _read_raw_sheets(source: Source, filename: str) -> dict[str, pd.DataFrame]:
    """Read every sheet of a file as raw (header-less) DataFrames.

    CSV files are exposed as a single pseudo-sheet named ``"csv"``.
    """
    lower = filename.lower()
    if lower.endswith(".csv"):
        buf = io.StringIO(source.decode("utf-8")) if isinstance(source, bytes) else source
        return {"csv": pd.read_csv(buf, header=None, dtype=object)}

    excel_source: Any = io.BytesIO(source) if isinstance(source, bytes) else source
    sheets = pd.read_excel(
        excel_source,
        engine=excel_engine_for(filename),
        sheet_name=None,
        header=None,
        dtype=object,
    )
    return sheets


def parse_workbook(source: Source, filename: str) -> WorkbookParseResult:
    """Single entry point: read a file and return normalized rows + issues.

    Empty sheets are skipped (with an info issue). Per-sheet semantics such as
    using the sheet name as the model and cross-sheet dedup are TR-04c.
    """
    result = WorkbookParseResult()
    raw_sheets = _read_raw_sheets(source, filename)

    for sheet_name, raw in raw_sheets.items():
        if raw is None or raw.empty:
            result.issues.append(
                ParseIssue(
                    level="info",
                    message="Sheet is empty; skipped.",
                    sheet=sheet_name,
                )
            )
            continue
        table = parse_sheet(raw, sheet_name=sheet_name)
        result.tables.append(table)
        result.issues.extend(table.issues)

    return result
