"""Unit tests for ReportService."""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import pandas as pd
from fastapi import Response

from app.services.report import ReportService
from app.models.models import Unit, Location, Transfer, Import, UnitStatus, TransferStatus


# ---------------------------------------------------------------------------
# get_dashboard_stats
# ---------------------------------------------------------------------------

def test_get_dashboard_stats():
    """Returns dashboard stats with all expected keys."""
    mock_db = MagicMock()
    mock_db.query.return_value.count.return_value = 0
    mock_db.query.return_value.options.return_value.order_by.return_value.limit.return_value.all.return_value = []
    mock_db.query.return_value.join.return_value.group_by.return_value.all.return_value = []
    mock_db.query.return_value.group_by.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = []

    result = ReportService.get_dashboard_stats(mock_db)

    assert "units" in result
    assert "locations" in result
    assert "transfers" in result
    assert "recent_transfers" in result
    assert "inventory_by_location" in result
    assert "inventory_by_brand" in result
    assert "sales_by_month" in result
    assert "recent_imports" in result
    assert "total" in result["units"]
    assert "available" in result["units"]
    assert "sold" in result["units"]
    assert "in_transit" in result["units"]


def test_get_dashboard_stats_empty_db():
    """Dashboard stats with empty DB returns expected structure."""
    mock_db = MagicMock()
    mock_db.query.return_value.count.return_value = 0
    mock_db.query.return_value.options.return_value.order_by.return_value.limit.return_value.all.return_value = []
    mock_db.query.return_value.join.return_value.group_by.return_value.all.return_value = []
    mock_db.query.return_value.group_by.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = []

    result = ReportService.get_dashboard_stats(mock_db)

    assert "units" in result
    assert "locations" in result
    assert "transfers" in result


# ---------------------------------------------------------------------------
# get_inventory_report
# ---------------------------------------------------------------------------

def test_get_inventory_report_no_filters():
    """Returns inventory report without filters."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.all.return_value = []

    result = ReportService.get_inventory_report(mock_db)

    assert "total_units" in result
    assert "summary" in result
    assert "units" in result
    assert result["total_units"] == 0


def test_get_inventory_report_with_filters():
    """Applies filters to inventory query."""
    mock_db = MagicMock()
    unit = Unit(id=1, brand="Thunderrol", model="TR", color="Red",
                status=UnitStatus.AVAILABLE, engine_number="E1")
    unit.current_location = Location(id=1, name="Bodega")
    mock_db.query.return_value.options.return_value.filter.return_value.filter.return_value.all.return_value = [unit]

    result = ReportService.get_inventory_report(
        mock_db, brand="Thunderrol", status=UnitStatus.AVAILABLE
    )

    assert result["total_units"] == 1
    assert "AVAILABLE" in result["summary"]["by_status"]


def test_get_inventory_report_no_results():
    """Returns empty report when no units match filters."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = []

    result = ReportService.get_inventory_report(mock_db, brand="NonExistent")

    assert result["total_units"] == 0
    assert result["units"] == []


# ---------------------------------------------------------------------------
# get_transfers_report
# ---------------------------------------------------------------------------

def test_get_transfers_report():
    """Returns transfers report with pagination."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    mock_db.query.return_value.options.return_value.count.return_value = 0
    mock_db.query.return_value.group_by.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = []

    result = ReportService.get_transfers_report(mock_db, skip=0, limit=10)

    assert "total_transfers" in result
    assert "summary" in result
    assert "transfers" in result
    assert "pagination" in result
    assert result["pagination"]["skip"] == 0
    assert result["pagination"]["limit"] == 10


def test_get_transfers_report_pagination():
    """Pagination metadata is correct."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []
    mock_db.query.return_value.options.return_value.count.return_value = 25
    mock_db.query.return_value.group_by.return_value.all.return_value = []
    mock_db.query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = []

    result = ReportService.get_transfers_report(mock_db, skip=10, limit=10)

    assert result["pagination"]["has_next"] is True
    assert result["pagination"]["has_previous"] is True


# ---------------------------------------------------------------------------
# get_sales_report
# ---------------------------------------------------------------------------

def test_get_sales_report():
    """Returns sales report."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = []

    result = ReportService.get_sales_report(mock_db)

    assert "total_sales" in result
    assert "summary" in result
    assert "sales" in result


def test_get_sales_report_by_location():
    """Filters sales by location using subquery."""
    mock_db = MagicMock()
    mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = []

    result = ReportService.get_sales_report(mock_db, location_id=1)

    assert result["total_sales"] == 0


# ---------------------------------------------------------------------------
# _prepare_df_for_excel
# ---------------------------------------------------------------------------

def test_prepare_df_for_excel_strips_timezone():
    """Removes timezone info from datetime columns."""
    df = pd.DataFrame({
        "name": ["A", "B"],
        "created_at": [
            datetime(2025, 1, 1, tzinfo=timezone.utc),
            datetime(2025, 6, 1, tzinfo=timezone.utc),
        ],
    })

    result = ReportService._prepare_df_for_excel(df)

    assert result["created_at"].dtype.name.startswith("datetime")
    assert result["created_at"].iloc[0].tzinfo is None
    assert result["created_at"].iloc[1].tzinfo is None


def test_prepare_df_for_excel_no_datetime_columns():
    """Leaves non-datetime columns unchanged."""
    df = pd.DataFrame({"name": ["A"], "count": [1]})
    result = ReportService._prepare_df_for_excel(df)
    assert list(result.columns) == ["name", "count"]


# ---------------------------------------------------------------------------
# export_inventory_excel
# ---------------------------------------------------------------------------

@patch.object(ReportService, "get_inventory_report")
def test_export_inventory_excel(mock_report):
    """Returns a Response with Excel content-type."""
    mock_db = MagicMock()
    mock_report.return_value = {
        "units": [{"id": 1, "brand": "T", "model": "M"}],
        "summary": {"by_status": {"available": 1}},
    }

    result = ReportService.export_inventory_excel(mock_db)

    assert isinstance(result, Response)
    assert "spreadsheetml" in result.media_type
    assert "attachment" in result.headers["content-disposition"]


# ---------------------------------------------------------------------------
# export_sales_excel
# ---------------------------------------------------------------------------

@patch.object(ReportService, "get_sales_report")
def test_export_sales_excel(mock_report):
    """Returns a Response with Excel content-type."""
    mock_db = MagicMock()
    mock_report.return_value = {
        "sales": [{"id": 1, "brand": "T"}],
        "summary": {"by_month": [{"month": "2025-01", "count": 1}]},
    }

    result = ReportService.export_sales_excel(mock_db)

    assert isinstance(result, Response)
    assert "spreadsheetml" in result.media_type
