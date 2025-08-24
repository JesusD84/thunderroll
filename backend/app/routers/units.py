
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc
from typing import List, Optional
from app.database.database import get_db
from app.models import models, schemas
from app.models.models import UserRole, UnitStatus, MovementType
from app.services.auth import get_current_active_user, require_role

router = APIRouter()

@router.get("/", response_model=List[schemas.Unit])
def get_units(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[UnitStatus] = None,
    brand_id: Optional[int] = None,
    model_id: Optional[int] = None,
    color_id: Optional[int] = None,
    location_id: Optional[int] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.Unit).options(
        selectinload(models.Unit.model).selectinload(models.Model.brand),
        selectinload(models.Unit.color),
        selectinload(models.Unit.current_location)
    )
    
    # Apply filters
    if status:
        query = query.filter(models.Unit.status == status)
    if brand_id:
        query = query.join(models.Model).filter(models.Model.brand_id == brand_id)
    if model_id:
        query = query.filter(models.Unit.model_id == model_id)
    if color_id:
        query = query.filter(models.Unit.color_id == color_id)
    if location_id:
        query = query.filter(models.Unit.current_location_id == location_id)
    if search:
        query = query.filter(
            or_(
                models.Unit.engine_number.ilike(f"%{search}%"),
                models.Unit.chassis_number.ilike(f"%{search}%")
            )
        )
    
    # Apply pagination and ordering
    query = query.order_by(desc(models.Unit.created_at))
    units = query.offset(skip).limit(limit).all()
    
    return units

@router.get("/stats")
def get_unit_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    total_units = db.query(models.Unit).count()
    available_units = db.query(models.Unit).filter(models.Unit.status == UnitStatus.AVAILABLE).count()
    sold_units = db.query(models.Unit).filter(models.Unit.status == UnitStatus.SOLD).count()
    in_transit_units = db.query(models.Unit).filter(models.Unit.status == UnitStatus.IN_TRANSIT).count()
    reserved_units = db.query(models.Unit).filter(models.Unit.status == UnitStatus.RESERVED).count()
    damaged_units = db.query(models.Unit).filter(models.Unit.status == UnitStatus.DAMAGED).count()
    maintenance_units = db.query(models.Unit).filter(models.Unit.status == UnitStatus.MAINTENANCE).count()
    
    # Get inventory by location
    inventory_by_location = db.query(
        models.Location.name,
        db.func.count(models.Unit.id).label("count")
    ).join(models.Unit, models.Unit.current_location_id == models.Location.id, isouter=True) \
     .group_by(models.Location.id, models.Location.name).all()
    
    return {
        "total_units": total_units,
        "available_units": available_units,
        "sold_units": sold_units,
        "in_transit_units": in_transit_units,
        "reserved_units": reserved_units,
        "damaged_units": damaged_units,
        "maintenance_units": maintenance_units,
        "inventory_by_location": [{"location": loc.name, "count": loc.count} for loc in inventory_by_location]
    }

@router.get("/{unit_id}", response_model=schemas.Unit)
def get_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    unit = db.query(models.Unit).options(
        selectinload(models.Unit.model).selectinload(models.Model.brand),
        selectinload(models.Unit.color),
        selectinload(models.Unit.current_location)
    ).filter(models.Unit.id == unit_id).first()
    
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit

@router.post("/", response_model=schemas.Unit)
def create_unit(
    unit: schemas.UnitCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    # Check if engine number or chassis number already exists
    existing_unit = db.query(models.Unit).filter(
        or_(
            models.Unit.engine_number == unit.engine_number,
            models.Unit.chassis_number == unit.chassis_number
        )
    ).first()
    
    if existing_unit:
        raise HTTPException(
            status_code=400,
            detail="Unit with this engine number or chassis number already exists"
        )
    
    # Create new unit
    db_unit = models.Unit(**unit.dict())
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    
    # Create import movement record
    movement = models.Movement(
        unit_id=db_unit.id,
        user_id=current_user.id,
        movement_type=MovementType.IMPORT,
        to_location_id=unit.current_location_id,
        notes="Unit created manually"
    )
    db.add(movement)
    db.commit()
    
    return get_unit(db_unit.id, db, current_user)

@router.put("/{unit_id}", response_model=schemas.Unit)
def update_unit(
    unit_id: int,
    unit_update: schemas.UnitUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    db_unit = db.query(models.Unit).filter(models.Unit.id == unit_id).first()
    if not db_unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    
    # Check for duplicate engine/chassis numbers if they're being updated
    update_data = unit_update.dict(exclude_unset=True)
    
    if "engine_number" in update_data or "chassis_number" in update_data:
        engine_check = update_data.get("engine_number", db_unit.engine_number)
        chassis_check = update_data.get("chassis_number", db_unit.chassis_number)
        
        existing_unit = db.query(models.Unit).filter(
            and_(
                models.Unit.id != unit_id,
                or_(
                    models.Unit.engine_number == engine_check,
                    models.Unit.chassis_number == chassis_check
                )
            )
        ).first()
        
        if existing_unit:
            raise HTTPException(
                status_code=400,
                detail="Another unit with this engine number or chassis number already exists"
            )
    
    # Track location changes for movement records
    old_location_id = db_unit.current_location_id
    old_status = db_unit.status
    
    # Update unit fields
    for field, value in update_data.items():
        setattr(db_unit, field, value)
    
    db.commit()
    db.refresh(db_unit)
    
    # Create movement record for location changes
    if "current_location_id" in update_data and update_data["current_location_id"] != old_location_id:
        movement = models.Movement(
            unit_id=db_unit.id,
            user_id=current_user.id,
            movement_type=MovementType.TRANSFER,
            from_location_id=old_location_id,
            to_location_id=update_data["current_location_id"],
            notes="Unit location updated"
        )
        db.add(movement)
        db.commit()
    
    # Create movement record for status changes
    if "status" in update_data and update_data["status"] != old_status:
        movement_type = MovementType.SALE if update_data["status"] == UnitStatus.SOLD else MovementType.TRANSFER
        movement = models.Movement(
            unit_id=db_unit.id,
            user_id=current_user.id,
            movement_type=movement_type,
            price=update_data.get("sale_price") if movement_type == MovementType.SALE else None,
            notes=f"Status changed from {old_status} to {update_data['status']}"
        )
        db.add(movement)
        db.commit()
    
    return get_unit(unit_id, db, current_user)

@router.delete("/{unit_id}")
def delete_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN]))
):
    db_unit = db.query(models.Unit).filter(models.Unit.id == unit_id).first()
    if not db_unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    
    # Check if unit has movements (except creation)
    movement_count = db.query(models.Movement).filter(
        and_(
            models.Movement.unit_id == unit_id,
            models.Movement.movement_type != MovementType.IMPORT
        )
    ).count()
    
    if movement_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete unit with movement history. Consider marking as inactive instead."
        )
    
    db.delete(db_unit)
    db.commit()
    return {"message": "Unit deleted successfully"}

@router.get("/{unit_id}/movements", response_model=List[schemas.Movement])
def get_unit_movements(
    unit_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Check if unit exists
    unit = db.query(models.Unit).filter(models.Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    
    movements = db.query(models.Movement).options(
        selectinload(models.Movement.user),
        selectinload(models.Movement.from_location),
        selectinload(models.Movement.to_location)
    ).filter(models.Movement.unit_id == unit_id) \
     .order_by(desc(models.Movement.created_at)) \
     .offset(skip).limit(limit).all()
    
    return movements

@router.post("/{unit_id}/move")
def move_unit(
    unit_id: int,
    movement: schemas.MovementCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    # Check if unit exists
    unit = db.query(models.Unit).filter(models.Unit.id == unit_id).first()
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    
    # Create movement record
    db_movement = models.Movement(
        **movement.dict(),
        unit_id=unit_id,
        user_id=current_user.id
    )
    db.add(db_movement)
    
    # Update unit location and status if applicable
    if movement.to_location_id:
        unit.current_location_id = movement.to_location_id
    
    if movement.movement_type == MovementType.SALE:
        unit.status = UnitStatus.SOLD
        if movement.price:
            unit.sale_price = movement.price
        unit.sold_date = movement.movement_date or db.func.now()
    elif movement.movement_type == MovementType.TRANSFER:
        unit.status = UnitStatus.IN_TRANSIT
    
    db.commit()
    db.refresh(db_movement)
    
    return {"message": "Unit moved successfully", "movement_id": db_movement.id}
