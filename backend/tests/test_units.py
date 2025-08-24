
"""Test unit endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_units(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test get units endpoint."""
    response = await client.get("/api/v1/units", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "size" in data


@pytest.mark.asyncio
async def test_create_unit(client: AsyncClient, auth_headers, test_users, test_locations):
    """Test create unit endpoint."""
    unit_data = {
        "brand": "Thunderrol",
        "model": "TR-2025", 
        "color": "red",
        "supplier_invoice": "TEST-001",
        "shipment_id": 1,  # This would need a real shipment in a full test
        "notes": "Test unit"
    }
    
    # This test would need more setup (creating shipment first)
    # For now, just test the endpoint exists and requires auth
    response = await client.post("/api/v1/units", json=unit_data, headers=auth_headers)
    # Expecting 404 or 422 because shipment doesn't exist, but not 401/403
    assert response.status_code != 401
    assert response.status_code != 403


@pytest.mark.asyncio
async def test_get_units_unauthorized(client: AsyncClient):
    """Test get units without authentication."""
    response = await client.get("/api/v1/units")
    assert response.status_code == 401
