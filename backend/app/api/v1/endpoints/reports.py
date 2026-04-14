
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
import io

from app.database.database import get_db
from app.models import models, schemas
from app.models.models import UserRole, UnitStatus, TransferType, TransferStatus
from app.services.auth_service import get_current_active_user, require_role

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Get dashboard statistics"""
    
    # Basic unit counts
    total_units = db.query(models.Unit).count()
    available_units = db.query(models.Unit).filter(models.Unit.status == UnitStatus.AVAILABLE).count()
    sold_units = db.query(models.Unit).filter(models.Unit.status == UnitStatus.SOLD).count()
    in_transit_units = db.query(models.Unit).filter(models.Unit.status == UnitStatus.IN_TRANSIT).count()
    
    # Location counts
    total_locations = db.query(models.Location).count()
    
    # Recent transfers (last 10)
    recent_transfers = db.query(models.Transfer).options(
        selectinload(models.Transfer.user),
        selectinload(models.Transfer.from_location),
        selectinload(models.Transfer.to_location)
    ).order_by(desc(models.Transfer.created_at)).limit(10).all()
    
    # Inventory by location
    inventory_by_location = db.query(
        models.Location.name.label("location"),
        func.count(models.Unit.id).label("count")
    ).join(models.Unit, models.Unit.current_location_id == models.Location.id, isouter=True) \
     .group_by(models.Location.id, models.Location.name).all()
    
    # Sales by month (last 6 months)
    six_months_ago = datetime.now() - timedelta(days=180)
    sales_by_month = db.query(
        func.date_trunc('month', models.Unit.sold_date).label("month"),
        func.count(models.Unit.id).label("count")
    ).filter(
        and_(
            models.Unit.status == UnitStatus.SOLD,
            models.Unit.sold_date >= six_months_ago
        )
    ).group_by(func.date_trunc('month', models.Unit.sold_date)) \
     .order_by(func.date_trunc('month', models.Unit.sold_date)).all()
    
    # Recent imports
    recent_imports = db.query(models.Import).options(
        selectinload(models.Import.user)
    ).order_by(desc(models.Import.import_date)).limit(5).all()
    
    # Active transfers
    active_transfers = db.query(models.Transfer).filter(
        models.Transfer.status.in_([TransferStatus.PENDING, TransferStatus.IN_TRANSIT])
    ).count()
    
    return {
        "units": {
            "total": total_units,
            "available": available_units,
            "sold": sold_units,
            "in_transit": in_transit_units,
        },
        "locations": {
            "total": total_locations
        },
        "transfers": {
            "active": active_transfers
        },
        "recent_transfers": [
            {
                "id": m.id,
                "unit_engine": m.unit.engine_number if m.unit else None,
                "transfer_type": m.transfer_type,
                "from_location": m.from_location.name if m.from_location else None,
                "to_location": m.to_location.name if m.to_location else None,
                "user": f"{m.user.first_name} {m.user.last_name}" if m.user else None,
                "date": m.transfer_date or m.created_at,
            } for m in recent_transfers
        ],
        "inventory_by_location": [
            {"location": item.location, "count": item.count}
            for item in inventory_by_location
        ],
        "inventory_by_brand": [
            {"brand": item.brand, "count": item.count}
            for item in inventory_by_brand
        ],
        "sales_by_month": [
            {
                "month": item.month.strftime("%Y-%m") if item.month else None,
                "count": item.count,
                "total_value": float(item.total_value) if item.total_value else 0
            } for item in sales_by_month
        ],
        "recent_imports": [
            {
                "id": imp.id,
                "filename": imp.original_filename,
                "total_records": imp.total_records,
                "successful": imp.successful_imports,
                "failed": imp.failed_imports,
                "date": imp.import_date,
                "user": f"{imp.user.first_name} {imp.user.last_name}" if imp.user else None
            } for imp in recent_imports
        ]
    }

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
    current_user: models.User = Depends(get_current_active_user)
):
    """Generate inventory report with filters"""
    
    query = db.query(models.Unit).options(
        selectinload(models.Unit.current_location)
    )
    
    # Apply filters
    if brand:
        query = query.filter(models.Unit.brand == brand)
    if model:
        query = query.filter(models.Unit.model == model)
    if color:
        query = query.filter(models.Unit.color == color)
    if location_id:
        query = query.filter(models.Unit.current_location_id == location_id)
    if status:
        query = query.filter(models.Unit.status == status)
    if date_from:
        query = query.filter(models.Unit.created_at >= date_from)
    if date_to:
        query = query.filter(models.Unit.created_at <= date_to)
    
    units = query.all()
    
    # Summary statistics
    total_units = len(units)
    by_status = {}
    by_location = {}
    by_brand = {}
    by_model = {}
    
    for unit in units:
        # By status
        status_key = unit.status.value if unit.status else "unknown"
        by_status[status_key] = by_status.get(status_key, 0) + 1
        
        # By location
        location_key = unit.current_location.name if unit.current_location else "No Location"
        by_location[location_key] = by_location.get(location_key, 0) + 1
    
    return {
        "total_units": total_units,
        "summary": {
            "by_status": by_status,
            "by_location": by_location,
            "by_brand": by_brand,
            "by_model": by_model
        },
        "units": [
            {
                "id": unit.id,
                "engine_number": unit.engine_number,
                "chassis_number": unit.chassis_number,
                "brand": unit.brand,
                "model": unit.model,
                "color": unit.color,
                "location": unit.current_location.name if unit.current_location else None,
                "status": unit.status.value if unit.status else None,
                "created_at": unit.created_at,
                "sold_date": unit.sold_date
            } for unit in units
        ]
    }

@router.get("/transfers")
def get_transfers_report(
    transfer_type: Optional[TransferType] = None,
    user_id: Optional[int] = None,
    location_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Generate transfers report with filters"""
    
    query = db.query(models.Transfer).options(
        selectinload(models.Transfer.user),
        selectinload(models.Transfer.from_location),
        selectinload(models.Transfer.to_location)
    )
    
    # Apply filters
    if transfer_type:
        query = query.filter(models.Transfer.transfer_type == transfer_type)
    if user_id:
        query = query.filter(models.Transfer.user_id == user_id)
    if location_id:
        query = query.filter(
            or_(
                models.Transfer.from_location_id == location_id,
                models.Transfer.to_location_id == location_id
            )
        )
    if date_from:
        query = query.filter(models.Transfer.transfer_date >= date_from)
    if date_to:
        query = query.filter(models.Transfer.transfer_date <= date_to)
    
    # Get total count for pagination
    total_transfers = query.count()
    
    # Apply pagination and ordering
    transfers = query.order_by(desc(models.Transfer.transfer_date)) \
                    .offset(skip).limit(limit).all()
    
    # Summary statistics
    by_type = db.query(
        models.Transfer.transfer_type,
        func.count(models.Transfer.id).label("count")
    ).group_by(models.Transfer.transfer_type).all()
    
    by_month = db.query(
        func.date_trunc('month', models.Transfer.transfer_date).label("month"),
        func.count(models.Transfer.id).label("count")
    ).group_by(func.date_trunc('month', models.Transfer.transfer_date)) \
     .order_by(func.date_trunc('month', models.Transfer.transfer_date)).all()
    
    return {
        "total_transfers": total_transfers,
        "summary": {
            "by_type": {item.transfer_type.value: item.count for item in by_type},
            "by_month": [
                {
                    "month": item.month.strftime("%Y-%m") if item.month else None,
                    "count": item.count
                } for item in by_month
            ]
        },
        "transfers": [
            {
                "id": transfer.id,
                "unit_engine": transfer.unit.engine_number if transfer.unit else None,
                "unit_chassis": transfer.unit.chassis_number if transfer.unit else None,
                "transfer_type": transfer.transfer_type.value if transfer.transfer_type else None,
                "from_location": transfer.from_location.name if transfer.from_location else None,
                "to_location": transfer.to_location.name if transfer.to_location else None,
                "user": f"{transfer.user.first_name} {transfer.user.last_name}" if transfer.user else None,
                "quantity": transfer.quantity,
                "notes": transfer.notes,
                "transfer_date": transfer.transfer_date,
                "created_at": transfer.created_at
            } for transfer in transfers
        ],
        "pagination": {
            "skip": skip,
            "limit": limit,
            "total": total_transfers,
            "has_next": skip + limit < total_transfers,
            "has_previous": skip > 0
        }
    }

@router.get("/sales")
def get_sales_report(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    location_id: Optional[int] = None,
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Generate sales report"""
    
    query = db.query(models.Unit).options(
        selectinload(models.Unit.current_location)
    ).filter(models.Unit.status == UnitStatus.SOLD)
    
    # Apply filters
    if date_from:
        query = query.filter(models.Unit.sold_date >= date_from)
    if date_to:
        query = query.filter(models.Unit.sold_date <= date_to)
    if location_id:
        # Find sales transfers for this location
        sold_units = db.query(models.Transfer.unit_id).filter(
            and_(
                models.Transfer.transfer_type == TransferType.SALE,
                or_(
                    models.Transfer.from_location_id == location_id,
                    models.Transfer.to_location_id == location_id
                )
            )
        ).subquery()
        query = query.filter(models.Unit.id.in_(sold_units))
    
    sold_units = query.all()
    
    # Calculate totals
    total_sales = len(sold_units)
    
    # Sales by month
    sales_by_month = {}
    for unit in sold_units:
        if unit.sold_date:
            month_key = unit.sold_date.strftime("%Y-%m")
            if month_key not in sales_by_month:
                sales_by_month[month_key] = {"count": 0}
            sales_by_month[month_key]["count"] += 1
    
    return {
        "total_sales": total_sales,

        "summary": {
            "by_month": [
                {
                    "month": month,
                    "count": data["count"]
                } for month, data in sorted(sales_by_month.items())
            ],
        },
        "sales": [
            {
                "id": unit.id,
                "engine_number": unit.engine_number,
                "chassis_number": unit.chassis_number,
                "brand": unit.brand,
                "model": unit.model,
                "color": unit.color,
                "sold_date": unit.sold_date
            } for unit in sold_units
        ]
    }

@router.get("/export/inventory")
def export_inventory_excel(
    brand: Optional[str] = None,
    model: Optional[str] = None,
    location_id: Optional[int] = None,
    status: Optional[UnitStatus] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Export inventory report to Excel"""
    
    # Get inventory data
    report_data = get_inventory_report(
        brand=brand,
        model=model,
        location_id=location_id,
        status=status,
        db=db,
        current_user=current_user
    )
    
    # Create DataFrame
    df = pd.DataFrame(report_data["units"])
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Inventory', index=False)
        
        # Add summary sheet
        summary_data = []
        for category, data in report_data["summary"].items():
            for key, value in data.items():
                summary_data.append({
                    "Category": category,
                    "Item": key,
                    "Count": value
                })
        
        pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
    
    output.seek(0)
    
    # Return Excel file
    filename = f"inventory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/export/transfers")
def export_transfers_excel(
    transfer_type: Optional[TransferType] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Export transfers report to Excel"""
    
    # Get transfers data (without pagination for export)
    report_data = get_transfers_report(
        transfer_type=transfer_type,
        date_from=date_from,
        date_to=date_to,
        limit=10000,  # Large limit for export
        db=db,
        current_user=current_user
    )
    
    # Create DataFrame
    df = pd.DataFrame(report_data["transfers"])
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Transfers', index=False)
    
    output.seek(0)
    
    # Return Excel file
    filename = f"transfers_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
