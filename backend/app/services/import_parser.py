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
import numbers
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

# Identifier fields whose values must be kept as exact strings (no scientific
# notation, no lost leading zeros, alphanumerics intact). See TR-04d.
ID_FIELDS: tuple[str, ...] = ("frame", "motor")

# Descriptive (category) fields that may live in merged cells spanning several
# rows; their column is forward-filled so every unit keeps the value (TR-04e).
# Identifier fields are deliberately excluded: a blank frame/motor means the
# value is missing, never that it repeats the row above.
FORWARD_FILL_FIELDS: tuple[str, ...] = ("model",)


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

        Only includes fields resolved for the sheet. Identifier fields
        (``frame``/``motor``) are normalized to exact strings (TR-04d); mapping
        to the persistence model is TR-08.
        """
        result: dict[str, Any] = {}
        for field_name, col in self.field_map.items():
            value = self.values.get(col)
            if field_name in ID_FIELDS:
                result[field_name] = normalize_id_value(value)
            else:
                result[field_name] = value
        return result


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


def _ffill_column(rows: list[dict[str, Any]], col: str) -> None:
    """Forward-fill blank cells of ``col`` across already-materialized rows.

    Used after a manual mapping points a forward-fill field (e.g. ``model``) at a
    column that the automatic detection had not recognized, so merged cells in
    that column still propagate to every unit.
    """
    last: Any = None
    for row in rows:
        value = row.get(col)
        if _is_blank(value):
            if last is not None:
                row[col] = last
        else:
            last = value


def apply_manual_mapping(
    result: "WorkbookParseResult", column_to_field: dict[str, str]
) -> list[ParseIssue]:
    """Override the auto-detected mapping with a user-confirmed one (TR-07).

    ``column_to_field`` maps a (normalized) column name to a canonical field. It
    is applied per sheet, only for columns that exist in that sheet, and a column
    is assigned to exactly one field (any prior field pointing at that column is
    cleared). Entries with an unknown canonical field are ignored. Forward-fill
    fields are re-filled so a newly mapped ``model`` column propagates its merged
    cells.
    """
    cleaned = {col: fld for col, fld in column_to_field.items() if fld in CANONICAL_FIELDS}
    issues: list[ParseIssue] = []
    if not cleaned:
        return issues

    for table in result.tables:
        applied = False
        for col, fld in cleaned.items():
            if col not in table.columns:
                continue
            for existing_field in [f for f, c in table.field_map.items() if c == col]:
                del table.field_map[existing_field]
            table.field_map[fld] = col
            applied = True
            issues.append(
                ParseIssue(
                    level="info",
                    message=f"Manual mapping: column '{col}' -> field '{fld}'.",
                    sheet=table.sheet,
                )
            )
        if applied:
            for fld in FORWARD_FILL_FIELDS:
                col = table.field_map.get(fld)
                if col is not None:
                    _ffill_column(table.rows, col)

    result.issues.extend(issues)
    return issues


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


def normalize_id_value(value: Any) -> str:
    """Normalize an identifier (frame/motor) cell to an exact string.

    Spreadsheets often store long serials as numbers, so a frame read back as a
    float would otherwise become ``"3.52e+14"`` or ``"352...0.0"``. This:
    - returns ``""`` for blank/NaN cells,
    - renders integral numbers without a decimal part or scientific notation
      (a 15-digit integer stays a 15-digit string),
    - keeps alphanumeric values (``ZT48V400W...``, ``YC-48V...``) and any
      existing string (incl. leading zeros) verbatim after trimming.
    """
    if _is_blank(value):
        return ""
    if isinstance(value, bool):
        # bool is a subclass of int; treat it as plain text, not 0/1.
        return str(value).strip()
    if isinstance(value, numbers.Integral):
        return str(int(value))
    if isinstance(value, numbers.Real):
        as_float = float(value)
        if as_float.is_integer():
            return str(int(as_float))
        return format(as_float, "f").rstrip("0").rstrip(".")
    return str(value).strip()


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

    # Drop fully-empty rows up front so they cannot receive a forward-filled
    # value (a blank row is not a merged cell, it is simply not a unit).
    data = data[~data.apply(lambda r: all(_is_blank(v) for v in r.tolist()), axis=1)].copy()

    # Forward-fill descriptive columns held in merged cells (e.g. a model that
    # only appears in the first row of its block). Never identifier columns.
    for field_name in FORWARD_FILL_FIELDS:
        col = field_map.get(field_name)
        if col is None:
            continue
        pos = columns.index(col)
        before = data.iloc[:, pos]
        filled = before.ffill()
        n_filled = int((before.isna() & filled.notna()).sum())
        if n_filled:
            data.iloc[:, pos] = filled
            issues.append(
                ParseIssue(
                    level="info",
                    message=(
                        f"Forward-filled {n_filled} merged cell(s) in "
                        f"'{field_name}' column ('{col}')."
                    ),
                    sheet=sheet_name,
                )
            )

    # Unmapped columns (index columns, colour legends, blank junk) carry no
    # canonical field and are ignored by ``SheetRow.canonical()``; surface them
    # as info so the drop is visible. Skipped for the all-positional no-header
    # case, which already warns about positional mapping.
    if has_header:
        ignored = [c for c in columns if c not in field_map.values()]
        if ignored:
            issues.append(
                ParseIssue(
                    level="info",
                    message=f"Ignoring {len(ignored)} unmapped column(s): {', '.join(ignored)}.",
                    sheet=sheet_name,
                )
            )

    rows: list[dict[str, Any]] = [
        {columns[i]: series.tolist()[i] for i in range(width)}
        for _, series in data.iterrows()
    ]

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
