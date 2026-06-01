"""Test report endpoints."""

from datetime import datetime

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_dashboard_stats(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test dashboard stats endpoint."""
    response = await client.get("/api/v1/reports/dashboard", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "units" in data
    assert "locations" in data
    assert "transfers" in data
    assert "recent_transfers" in data
    assert "inventory_by_location" in data
    assert "inventory_by_brand" in data
    assert "sales_by_month" in data
    assert "recent_imports" in data
    assert data["units"]["total"] >= 0
    assert data["units"]["available"] >= 0
    assert data["units"]["sold"] >= 0
    assert data["units"]["in_transit"] >= 0


@pytest.mark.asyncio
async def test_get_inventory_report(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test inventory report endpoint."""
    response = await client.get("/api/v1/reports/inventory", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "total_units" in data
    assert "summary" in data
    assert "units" in data
    assert "by_status" in data["summary"]
    assert "by_location" in data["summary"]


@pytest.mark.asyncio
async def test_get_inventory_report_with_filters(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test inventory report with filters."""
    response = await client.get(
        "/api/v1/reports/inventory",
        params={"brand": "Thunderrol", "status": "AVAILABLE"},
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    for unit in data["units"]:
        assert unit["brand"] == "Thunderrol"
        assert unit["status"] == "AVAILABLE"


@pytest.mark.asyncio
async def test_get_transfers_report(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test transfers report endpoint."""
    response = await client.get("/api/v1/reports/transfers", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "total_transfers" in data
    assert "summary" in data
    assert "transfers" in data
    assert "pagination" in data
    assert "by_status" in data["summary"]
    assert "by_month" in data["summary"]


@pytest.mark.asyncio
async def test_get_transfers_report_pagination(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test transfers report pagination."""
    response = await client.get(
        "/api/v1/reports/transfers",
        params={"skip": 0, "limit": 5},
        headers=auth_headers,
    )
    assert response.status_code == 200

    data = response.json()
    pagination = data["pagination"]
    assert pagination["skip"] == 0
    assert pagination["limit"] == 5
    assert "has_next" in pagination
    assert "has_previous" in pagination


@pytest.mark.asyncio
async def test_get_sales_report(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test sales report endpoint."""
    response = await client.get("/api/v1/reports/sales", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert "total_sales" in data
    assert "summary" in data
    assert "sales" in data
    assert "by_month" in data["summary"]


@pytest.mark.asyncio
async def test_export_inventory_excel(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test inventory Excel export endpoint."""
    response = await client.get("/api/v1/reports/export/inventory", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_transfers_excel(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test transfers Excel export endpoint."""
    response = await client.get("/api/v1/reports/export/transfers", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_sales_excel(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test sales Excel export endpoint."""
    response = await client.get("/api/v1/reports/export/sales", headers=auth_headers)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "attachment" in response.headers["content-disposition"]


@pytest.mark.asyncio
async def test_dashboard_sales_by_month_with_sold_unit(
    client: AsyncClient, auth_headers, sold_unit_with_history
):
    """Regression: dashboard must not 500 when a sold unit exists.

    The sales_by_month aggregation groups by a substr(cast(date, String))
    expression that already yields a 'YYYY-MM' string. The service previously
    called .strftime() on that string, raising AttributeError -> 500.
    """
    response = await client.get("/api/v1/reports/dashboard", headers=auth_headers)
    assert response.status_code == 200, response.text

    sales_by_month = response.json()["sales_by_month"]
    assert len(sales_by_month) >= 1
    current_month = datetime.now().strftime("%Y-%m")
    months = [row["month"] for row in sales_by_month]
    assert current_month in months
    for row in sales_by_month:
        assert isinstance(row["month"], str)
        assert len(row["month"]) == 7  # YYYY-MM


@pytest.mark.asyncio
async def test_transfers_report_by_month_with_transfer(
    client: AsyncClient, auth_headers, sold_unit_with_history
):
    """Regression: transfers report by_month must not 500 with existing transfers."""
    response = await client.get("/api/v1/reports/transfers", headers=auth_headers)
    assert response.status_code == 200, response.text

    by_month = response.json()["summary"]["by_month"]
    assert len(by_month) >= 1
    current_month = datetime.now().strftime("%Y-%m")
    months = [row["month"] for row in by_month]
    assert current_month in months
    for row in by_month:
        assert isinstance(row["month"], str)
        assert len(row["month"]) == 7  # YYYY-MM


@pytest.mark.asyncio
async def test_reports_require_auth(client: AsyncClient):
    """Test that report endpoints require authentication."""
    endpoints = [
        "/api/v1/reports/dashboard",
        "/api/v1/reports/inventory",
        "/api/v1/reports/transfers",
        "/api/v1/reports/sales",
        "/api/v1/reports/export/inventory",
        "/api/v1/reports/export/transfers",
        "/api/v1/reports/export/sales",
    ]

    for endpoint in endpoints:
        response = await client.get(endpoint)
        assert response.status_code == 401, f"Expected 401 for {endpoint}, got {response.status_code}"
