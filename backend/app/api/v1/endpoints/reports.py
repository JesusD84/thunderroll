
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models import models
from app.models.models import UnitStatus
from app.services.auth_service import get_current_active_user
from app.services.report import ReportService

router = APIRouter()


@router.get("/dashboard")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Get dashboard statistics."""
    return ReportService.get_dashboard_stats(db)


@router.get("/inventory")
def get_inventory_report(
    brand: Optional[str] = None,
    model: Optional[str] = None,
    color: Optional[str] = None,
    location_id: Optional[int] = None,
    status: Optional[UnitStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Generate inventory report with filters."""
    return ReportService.get_inventory_report(
        db,
        brand=brand,
        model=model,
        color=color,
        location_id=location_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/transfers")
def get_transfers_report(
    user_id: Optional[int] = None,
    location_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Generate transfers report with filters."""
    return ReportService.get_transfers_report(
        db,
        user_id=user_id,
        location_id=location_id,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )


@router.get("/sales")
def get_sales_report(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    location_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Generate sales report."""
    return ReportService.get_sales_report(
        db,
        date_from=date_from,
        date_to=date_to,
        location_id=location_id,
    )


@router.get("/export/inventory")
def export_inventory_excel(
    brand: Optional[str] = None,
    model: Optional[str] = None,
    location_id: Optional[int] = None,
    status: Optional[UnitStatus] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Export inventory report to Excel."""
    return ReportService.export_inventory_excel(
        db,
        brand=brand,
        model=model,
        location_id=location_id,
        status=status,
    )


@router.get("/export/transfers")
def export_transfers_excel(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Export transfers report to Excel."""
    return ReportService.export_transfers_excel(
        db,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/export/sales")
def export_sales_excel(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    location_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
):
    """Export sales report to Excel."""
    return ReportService.export_sales_excel(
        db,
        date_from=date_from,
        date_to=date_to,
        location_id=location_id,
    )
