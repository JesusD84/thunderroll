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
import re
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional, Union

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

# Canonical fields the parser resolves supplier columns into. Mapping these to
# the persistence model (chassis_number/engine_number/...) happens downstream.
CANONICAL_FIELDS: tuple[str, ...] = ("frame", "motor", "color", "model")

# Substring synonyms per canonical field, stored in normalized form (lowercased,
# whitespace removed) to match against normalized column labels. Order matters:
# a label is assigned to the first canonical field with a matching synonym.
FIELD_SYNONYMS: dict[str, tuple[str, ...]] = {
    "frame": ("frame", "chassis", "chasis", "vin", "车架"),
    "motor": ("motor", "engine", "电机", "发动机"),
    "color": ("color", "colour", "颜色"),
    "model": ("model", "modelo", "型号", "车型"),
}

_WHITESPACE = re.compile(r"\s+")


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
    # canonical field (frame/motor/color/model) -> resolved column name.
    field_map: dict[str, str] = field(default_factory=dict)
    issues: list[ParseIssue] = field(default_factory=list)


@dataclass
class SheetRow:
    """A single data row tagged with its source sheet and field mapping.

    This is the flattened, cross-sheet view consumers iterate over. The sheet
    name is preserved so downstream code (TR-05 model equivalence, TR-08
    persistence) can use it as the model when the file has no model column.
    """

    sheet: Optional[str]
    has_header: bool
    field_map: dict[str, str]
    values: dict[str, Any]

    def canonical(self) -> dict[str, Any]:
        """Return the row keyed by canonical field (frame/motor/color/model).

        Only includes fields resolved for the sheet. Type normalization of the
        values is TR-04d; mapping to the persistence model is TR-08.
        """
        return {field_name: self.values.get(col) for field_name, col in self.field_map.items()}


@dataclass
class WorkbookParseResult:
    """Aggregate result for a whole file (one entry per non-empty sheet)."""

    tables: list[ParsedTable] = field(default_factory=list)
    issues: list[ParseIssue] = field(default_factory=list)

    def iter_rows(self) -> Iterator[SheetRow]:
        """Iterate every data row across all sheets, tagged with its origin."""
        for table in self.tables:
            for values in table.rows:
                yield SheetRow(
                    sheet=table.sheet,
                    has_header=table.has_header,
                    field_map=table.field_map,
                    values=values,
                )


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


def normalize_label(value: Any) -> str:
    """Normalize a label for synonym matching: lowercase, strip all whitespace.

    Removing internal spaces and newlines lets a single synonym match noisy
    supplier labels like ``"Frame number"``, ``"Frame\nNo."`` or
    ``"车架号Frame serial number"``.
    """
    if _is_blank(value):
        return ""
    return _WHITESPACE.sub("", str(value).strip().lower())


def resolve_field(label: Any) -> Optional[str]:
    """Resolve a single column label to a canonical field, or ``None``.

    A label maps to the first canonical field (in ``FIELD_SYNONYMS`` order)
    that has a synonym contained in the normalized label.
    """
    norm = normalize_label(label)
    if not norm:
        return None
    for field_name, synonyms in FIELD_SYNONYMS.items():
        if any(syn in norm for syn in synonyms):
            return field_name
    return None


def resolve_columns(
    columns: list[str], sheet_name: Optional[str] = None
) -> tuple[dict[str, str], list[ParseIssue]]:
    """Map a list of column names to canonical fields.

    Returns ``(field_map, issues)`` where ``field_map`` is
    ``canonical_field -> column_name``. When several columns resolve to the
    same field, the first wins and a warning issue is emitted for the rest.
    """
    field_map: dict[str, str] = {}
    issues: list[ParseIssue] = []
    for col in columns:
        field_name = resolve_field(col)
        if field_name is None:
            continue
        if field_name in field_map:
            issues.append(
                ParseIssue(
                    level="warning",
                    message=(
                        f"Multiple columns map to '{field_name}': "
                        f"'{field_map[field_name]}' kept, '{col}' ignored."
                    ),
                    sheet=sheet_name,
                )
            )
            continue
        field_map[field_name] = col
    return field_map, issues


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

    # Resolve columns to canonical fields. Positional (no-header) columns like
    # ``col_0`` carry no synonyms, so this yields an empty map for Sample 3.
    field_map, field_issues = resolve_columns(columns, sheet_name=sheet_name)
    issues.extend(field_issues)

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
        field_map=field_map,
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

    Every sheet is read; sheets that are empty or yield no data rows are skipped
    with an info issue. Each surviving sheet keeps its name as ``ParsedTable.sheet``
    so the origin is available to downstream model resolution (TR-05). Use
    ``WorkbookParseResult.iter_rows()`` for a flattened, origin-tagged view.
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
        if not table.rows:
            # A sheet with only blank rows (or a header and no data) carries no
            # units; treat it like an empty sheet so it is not processed.
            result.issues.append(
                ParseIssue(
                    level="info",
                    message="Sheet has no data rows; skipped.",
                    sheet=sheet_name,
                )
            )
            continue
        result.tables.append(table)
        result.issues.extend(table.issues)

    return result
