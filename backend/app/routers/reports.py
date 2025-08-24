
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, desc, and_, or_
from datetime import datetime, timedelta
from typing import List, Optional
import pandas as pd
import io

from app.database.database import get_db
from app.models import models, schemas
from app.models.models import UserRole, UnitStatus, MovementType
from app.services.auth import get_current_active_user, require_role

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
    reserved_units = db.query(models.Unit).filter(models.Unit.status == UnitStatus.RESERVED).count()
    
    # Location counts
    total_locations = db.query(models.Location).filter(models.Location.is_active == True).count()
    
    # Recent movements (last 10)
    recent_movements = db.query(models.Movement).options(
        selectinload(models.Movement.unit).selectinload(models.Unit.model),
        selectinload(models.Movement.user),
        selectinload(models.Movement.from_location),
        selectinload(models.Movement.to_location)
    ).order_by(desc(models.Movement.created_at)).limit(10).all()
    
    # Inventory by location
    inventory_by_location = db.query(
        models.Location.name.label("location"),
        func.count(models.Unit.id).label("count")
    ).join(models.Unit, models.Unit.current_location_id == models.Location.id, isouter=True) \
     .filter(models.Location.is_active == True) \
     .group_by(models.Location.id, models.Location.name).all()
    
    # Inventory by brand
    inventory_by_brand = db.query(
        models.Brand.name.label("brand"),
        func.count(models.Unit.id).label("count")
    ).join(models.Model).join(models.Unit) \
     .filter(models.Brand.is_active == True) \
     .group_by(models.Brand.id, models.Brand.name).all()
    
    # Sales by month (last 6 months)
    six_months_ago = datetime.now() - timedelta(days=180)
    sales_by_month = db.query(
        func.date_trunc('month', models.Unit.sold_date).label("month"),
        func.count(models.Unit.id).label("count"),
        func.sum(models.Unit.sale_price).label("total_value")
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
        models.Transfer.status.in_(["pending", "in_transit"])
    ).count()
    
    return {
        "units": {
            "total": total_units,
            "available": available_units,
            "sold": sold_units,
            "in_transit": in_transit_units,
            "reserved": reserved_units
        },
        "locations": {
            "total": total_locations
        },
        "transfers": {
            "active": active_transfers
        },
        "recent_movements": [
            {
                "id": m.id,
                "unit_engine": m.unit.engine_number if m.unit else None,
                "movement_type": m.movement_type,
                "from_location": m.from_location.name if m.from_location else None,
                "to_location": m.to_location.name if m.to_location else None,
                "user": f"{m.user.first_name} {m.user.last_name}" if m.user else None,
                "date": m.movement_date or m.created_at,
                "price": m.price
            } for m in recent_movements
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
    brand_id: Optional[int] = None,
    model_id: Optional[int] = None,
    color_id: Optional[int] = None,
    location_id: Optional[int] = None,
    status: Optional[UnitStatus] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Generate inventory report with filters"""
    
    query = db.query(models.Unit).options(
        selectinload(models.Unit.model).selectinload(models.Model.brand),
        selectinload(models.Unit.color),
        selectinload(models.Unit.current_location)
    )
    
    # Apply filters
    if brand_id:
        query = query.join(models.Model).filter(models.Model.brand_id == brand_id)
    if model_id:
        query = query.filter(models.Unit.model_id == model_id)
    if color_id:
        query = query.filter(models.Unit.color_id == color_id)
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
        
        # By brand
        brand_key = unit.model.brand.name if unit.model and unit.model.brand else "Unknown Brand"
        by_brand[brand_key] = by_brand.get(brand_key, 0) + 1
        
        # By model
        model_key = f"{brand_key} {unit.model.name}" if unit.model else "Unknown Model"
        by_model[model_key] = by_model.get(model_key, 0) + 1
    
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
                "brand": unit.model.brand.name if unit.model and unit.model.brand else None,
                "model": unit.model.name if unit.model else None,
                "color": unit.color.name if unit.color else None,
                "location": unit.current_location.name if unit.current_location else None,
                "status": unit.status.value if unit.status else None,
                "purchase_price": unit.purchase_price,
                "sale_price": unit.sale_price,
                "created_at": unit.created_at,
                "sold_date": unit.sold_date
            } for unit in units
        ]
    }

@router.get("/movements")
def get_movements_report(
    movement_type: Optional[MovementType] = None,
    user_id: Optional[int] = None,
    location_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Generate movements report with filters"""
    
    query = db.query(models.Movement).options(
        selectinload(models.Movement.unit).selectinload(models.Unit.model),
        selectinload(models.Movement.user),
        selectinload(models.Movement.from_location),
        selectinload(models.Movement.to_location)
    )
    
    # Apply filters
    if movement_type:
        query = query.filter(models.Movement.movement_type == movement_type)
    if user_id:
        query = query.filter(models.Movement.user_id == user_id)
    if location_id:
        query = query.filter(
            or_(
                models.Movement.from_location_id == location_id,
                models.Movement.to_location_id == location_id
            )
        )
    if date_from:
        query = query.filter(models.Movement.movement_date >= date_from)
    if date_to:
        query = query.filter(models.Movement.movement_date <= date_to)
    
    # Get total count for pagination
    total_movements = query.count()
    
    # Apply pagination and ordering
    movements = query.order_by(desc(models.Movement.movement_date)) \
                    .offset(skip).limit(limit).all()
    
    # Summary statistics
    by_type = db.query(
        models.Movement.movement_type,
        func.count(models.Movement.id).label("count")
    ).group_by(models.Movement.movement_type).all()
    
    by_month = db.query(
        func.date_trunc('month', models.Movement.movement_date).label("month"),
        func.count(models.Movement.id).label("count")
    ).group_by(func.date_trunc('month', models.Movement.movement_date)) \
     .order_by(func.date_trunc('month', models.Movement.movement_date)).all()
    
    return {
        "total_movements": total_movements,
        "summary": {
            "by_type": {item.movement_type.value: item.count for item in by_type},
            "by_month": [
                {
                    "month": item.month.strftime("%Y-%m") if item.month else None,
                    "count": item.count
                } for item in by_month
            ]
        },
        "movements": [
            {
                "id": movement.id,
                "unit_engine": movement.unit.engine_number if movement.unit else None,
                "unit_chassis": movement.unit.chassis_number if movement.unit else None,
                "movement_type": movement.movement_type.value if movement.movement_type else None,
                "from_location": movement.from_location.name if movement.from_location else None,
                "to_location": movement.to_location.name if movement.to_location else None,
                "user": f"{movement.user.first_name} {movement.user.last_name}" if movement.user else None,
                "quantity": movement.quantity,
                "price": movement.price,
                "notes": movement.notes,
                "movement_date": movement.movement_date,
                "created_at": movement.created_at
            } for movement in movements
        ],
        "pagination": {
            "skip": skip,
            "limit": limit,
            "total": total_movements,
            "has_next": skip + limit < total_movements,
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
        selectinload(models.Unit.model).selectinload(models.Model.brand),
        selectinload(models.Unit.color),
        selectinload(models.Unit.current_location)
    ).filter(models.Unit.status == UnitStatus.SOLD)
    
    # Apply filters
    if date_from:
        query = query.filter(models.Unit.sold_date >= date_from)
    if date_to:
        query = query.filter(models.Unit.sold_date <= date_to)
    if location_id:
        # Find sales movements for this location
        sold_units = db.query(models.Movement.unit_id).filter(
            and_(
                models.Movement.movement_type == MovementType.SALE,
                or_(
                    models.Movement.from_location_id == location_id,
                    models.Movement.to_location_id == location_id
                )
            )
        ).subquery()
        query = query.filter(models.Unit.id.in_(sold_units))
    
    sold_units = query.all()
    
    # Calculate totals
    total_sales = len(sold_units)
    total_revenue = sum([unit.sale_price or 0 for unit in sold_units])
    total_profit = sum([
        (unit.sale_price or 0) - (unit.purchase_price or 0) 
        for unit in sold_units
    ])
    
    # Sales by month
    sales_by_month = {}
    for unit in sold_units:
        if unit.sold_date:
            month_key = unit.sold_date.strftime("%Y-%m")
            if month_key not in sales_by_month:
                sales_by_month[month_key] = {"count": 0, "revenue": 0}
            sales_by_month[month_key]["count"] += 1
            sales_by_month[month_key]["revenue"] += unit.sale_price or 0
    
    # Sales by brand
    sales_by_brand = {}
    for unit in sold_units:
        brand = unit.model.brand.name if unit.model and unit.model.brand else "Unknown"
        if brand not in sales_by_brand:
            sales_by_brand[brand] = {"count": 0, "revenue": 0}
        sales_by_brand[brand]["count"] += 1
        sales_by_brand[brand]["revenue"] += unit.sale_price or 0
    
    return {
        "total_sales": total_sales,
        "total_revenue": total_revenue,
        "total_profit": total_profit,
        "average_sale_price": total_revenue / total_sales if total_sales > 0 else 0,
        "summary": {
            "by_month": [
                {
                    "month": month,
                    "count": data["count"],
                    "revenue": data["revenue"]
                } for month, data in sorted(sales_by_month.items())
            ],
            "by_brand": [
                {
                    "brand": brand,
                    "count": data["count"],
                    "revenue": data["revenue"]
                } for brand, data in sorted(sales_by_brand.items(), key=lambda x: x[1]["revenue"], reverse=True)
            ]
        },
        "sales": [
            {
                "id": unit.id,
                "engine_number": unit.engine_number,
                "chassis_number": unit.chassis_number,
                "brand": unit.model.brand.name if unit.model and unit.model.brand else None,
                "model": unit.model.name if unit.model else None,
                "color": unit.color.name if unit.color else None,
                "purchase_price": unit.purchase_price,
                "sale_price": unit.sale_price,
                "profit": (unit.sale_price or 0) - (unit.purchase_price or 0),
                "sold_date": unit.sold_date
            } for unit in sold_units
        ]
    }

@router.get("/export/inventory")
def export_inventory_excel(
    brand_id: Optional[int] = None,
    model_id: Optional[int] = None,
    location_id: Optional[int] = None,
    status: Optional[UnitStatus] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Export inventory report to Excel"""
    
    # Get inventory data
    report_data = get_inventory_report(
        brand_id=brand_id,
        model_id=model_id,
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

@router.get("/export/movements")
def export_movements_excel(
    movement_type: Optional[MovementType] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """Export movements report to Excel"""
    
    # Get movements data (without pagination for export)
    report_data = get_movements_report(
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
        limit=10000,  # Large limit for export
        db=db,
        current_user=current_user
    )
    
    # Create DataFrame
    df = pd.DataFrame(report_data["movements"])
    
    # Create Excel file in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Movements', index=False)
    
    output.seek(0)
    
    # Return Excel file
    filename = f"movements_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
