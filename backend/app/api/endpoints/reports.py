
"""Report generation endpoints."""

from datetime import date
from typing import Dict, Any
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_ventas
from app.services.report import ReportService

router = APIRouter()


@router.get("/movements")
async def generate_movements_report(
    from_date: date = Query(..., description="Start date (YYYY-MM-DD)"),
    to_date: date = Query(..., description="End date (YYYY-MM-DD)"),
    format: str = Query("xlsx", regex="^(xlsx|csv)$", description="Export format"),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_ventas)
):
    """
    Generate movements report for date range.
    
    Returns Excel or CSV file with all unit movements in the specified period.
    Includes columns: timestamp, unit_id, event_type, from->to, user, batch, branch, notes.
    """
    
    response = await ReportService.generate_movements_report(
        db=db,
        from_date=from_date,
        to_date=to_date,
        format_type=format
    )
    
    return response


@router.get("/dashboard", response_model=Dict[str, Any])
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_ventas)
):
    """
    Get dashboard statistics.
    
    Returns KPIs including:
    - Units by status
    - Units by location
    - Recent events
    - Total units count
    """
    
    stats = await ReportService.get_dashboard_stats(db)
    return stats
