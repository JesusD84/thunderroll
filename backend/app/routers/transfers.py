
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional
from datetime import datetime

from app.database.database import get_db
from app.models import models, schemas
from app.models.models import UserRole, UnitStatus, MovementType
from app.services.auth import get_current_active_user, require_role

router = APIRouter()

@router.get("/", response_model=List[schemas.Transfer])
def get_transfers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    from_location_id: Optional[int] = None,
    to_location_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    query = db.query(models.Transfer).options(
        selectinload(models.Transfer.from_location),
        selectinload(models.Transfer.to_location),
        selectinload(models.Transfer.user)
    )
    
    # Apply filters
    if status:
        query = query.filter(models.Transfer.status == status)
    if from_location_id:
        query = query.filter(models.Transfer.from_location_id == from_location_id)
    if to_location_id:
        query = query.filter(models.Transfer.to_location_id == to_location_id)
    
    # Apply pagination and ordering
    transfers = query.order_by(desc(models.Transfer.created_at)) \
                    .offset(skip).limit(limit).all()
    
    return transfers

@router.get("/stats")
def get_transfer_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    total_transfers = db.query(models.Transfer).count()
    pending_transfers = db.query(models.Transfer).filter(models.Transfer.status == "pending").count()
    in_transit_transfers = db.query(models.Transfer).filter(models.Transfer.status == "in_transit").count()
    completed_transfers = db.query(models.Transfer).filter(models.Transfer.status == "completed").count()
    
    # Recent transfers
    recent_transfers = db.query(models.Transfer).options(
        selectinload(models.Transfer.from_location),
        selectinload(models.Transfer.to_location)
    ).order_by(desc(models.Transfer.created_at)).limit(5).all()
    
    return {
        "total_transfers": total_transfers,
        "pending_transfers": pending_transfers,
        "in_transit_transfers": in_transit_transfers,
        "completed_transfers": completed_transfers,
        "recent_transfers": recent_transfers
    }

@router.get("/{transfer_id}", response_model=schemas.Transfer)
def get_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    transfer = db.query(models.Transfer).options(
        selectinload(models.Transfer.from_location),
        selectinload(models.Transfer.to_location),
        selectinload(models.Transfer.user),
        selectinload(models.Transfer.transfer_units)
    ).filter(models.Transfer.id == transfer_id).first()
    
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    return transfer

@router.get("/{transfer_id}/units")
def get_transfer_units(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    transfer = db.query(models.Transfer).filter(models.Transfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    units = db.query(models.Unit).join(models.TransferUnit) \
              .filter(models.TransferUnit.transfer_id == transfer_id) \
              .options(
                  selectinload(models.Unit.model).selectinload(models.Model.brand),
                  selectinload(models.Unit.color)
              ).all()
    
    return units

@router.post("/", response_model=schemas.Transfer)
def create_transfer(
    transfer: schemas.TransferCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    # Validate locations exist
    from_location = db.query(models.Location).filter(models.Location.id == transfer.from_location_id).first()
    to_location = db.query(models.Location).filter(models.Location.id == transfer.to_location_id).first()
    
    if not from_location or not to_location:
        raise HTTPException(status_code=400, detail="Invalid location IDs")
    
    if transfer.from_location_id == transfer.to_location_id:
        raise HTTPException(status_code=400, detail="Source and destination locations cannot be the same")
    
    # Validate units exist and are available
    units = db.query(models.Unit).filter(models.Unit.id.in_(transfer.unit_ids)).all()
    
    if len(units) != len(transfer.unit_ids):
        raise HTTPException(status_code=400, detail="Some units not found")
    
    # Check if all units are available and at the source location
    invalid_units = []
    for unit in units:
        if unit.current_location_id != transfer.from_location_id:
            invalid_units.append(f"Unit {unit.engine_number} is not at the source location")
        if unit.status not in [UnitStatus.AVAILABLE, UnitStatus.RESERVED]:
            invalid_units.append(f"Unit {unit.engine_number} is not available for transfer")
    
    if invalid_units:
        raise HTTPException(status_code=400, detail="; ".join(invalid_units))
    
    # Create transfer record
    db_transfer = models.Transfer(
        from_location_id=transfer.from_location_id,
        to_location_id=transfer.to_location_id,
        user_id=current_user.id,
        total_units=len(transfer.unit_ids),
        notes=transfer.notes,
        transfer_date=transfer.transfer_date or datetime.utcnow()
    )
    db.add(db_transfer)
    db.commit()
    db.refresh(db_transfer)
    
    # Add units to transfer
    for unit_id in transfer.unit_ids:
        transfer_unit = models.TransferUnit(
            transfer_id=db_transfer.id,
            unit_id=unit_id
        )
        db.add(transfer_unit)
        
        # Update unit status
        unit = db.query(models.Unit).filter(models.Unit.id == unit_id).first()
        unit.status = UnitStatus.IN_TRANSIT
        
        # Create movement record
        movement = models.Movement(
            unit_id=unit_id,
            user_id=current_user.id,
            movement_type=MovementType.TRANSFER,
            from_location_id=transfer.from_location_id,
            to_location_id=transfer.to_location_id,
            notes=f"Transfer #{db_transfer.id} created"
        )
        db.add(movement)
    
    db.commit()
    
    return get_transfer(db_transfer.id, db, current_user)

@router.put("/{transfer_id}", response_model=schemas.Transfer)
def update_transfer(
    transfer_id: int,
    transfer_update: schemas.TransferUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    db_transfer = db.query(models.Transfer).filter(models.Transfer.id == transfer_id).first()
    if not db_transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    update_data = transfer_update.dict(exclude_unset=True)
    
    # Handle status changes
    if "status" in update_data:
        old_status = db_transfer.status
        new_status = update_data["status"]
        
        if old_status == "completed" and new_status != "completed":
            raise HTTPException(status_code=400, detail="Cannot change status of completed transfer")
        
        # If completing the transfer
        if new_status == "completed" and old_status != "completed":
            # Update all units in the transfer
            transfer_units = db.query(models.TransferUnit).filter(
                models.TransferUnit.transfer_id == transfer_id
            ).all()
            
            for transfer_unit in transfer_units:
                unit = db.query(models.Unit).filter(models.Unit.id == transfer_unit.unit_id).first()
                unit.current_location_id = db_transfer.to_location_id
                unit.status = UnitStatus.AVAILABLE
                
                # Create completion movement record
                movement = models.Movement(
                    unit_id=unit.id,
                    user_id=current_user.id,
                    movement_type=MovementType.TRANSFER,
                    from_location_id=db_transfer.from_location_id,
                    to_location_id=db_transfer.to_location_id,
                    notes=f"Transfer #{transfer_id} completed"
                )
                db.add(movement)
            
            update_data["completed_date"] = datetime.utcnow()
        
        # If cancelling the transfer
        elif new_status == "cancelled":
            # Reset unit statuses
            transfer_units = db.query(models.TransferUnit).filter(
                models.TransferUnit.transfer_id == transfer_id
            ).all()
            
            for transfer_unit in transfer_units:
                unit = db.query(models.Unit).filter(models.Unit.id == transfer_unit.unit_id).first()
                unit.status = UnitStatus.AVAILABLE
    
    # Update transfer fields
    for field, value in update_data.items():
        setattr(db_transfer, field, value)
    
    db.commit()
    db.refresh(db_transfer)
    
    return get_transfer(transfer_id, db, current_user)

@router.delete("/{transfer_id}")
def delete_transfer(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN]))
):
    db_transfer = db.query(models.Transfer).filter(models.Transfer.id == transfer_id).first()
    if not db_transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    if db_transfer.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot delete completed transfer")
    
    # Reset unit statuses
    if db_transfer.status in ["pending", "in_transit"]:
        transfer_units = db.query(models.TransferUnit).filter(
            models.TransferUnit.transfer_id == transfer_id
        ).all()
        
        for transfer_unit in transfer_units:
            unit = db.query(models.Unit).filter(models.Unit.id == transfer_unit.unit_id).first()
            unit.status = UnitStatus.AVAILABLE
    
    # Delete transfer units
    db.query(models.TransferUnit).filter(models.TransferUnit.transfer_id == transfer_id).delete()
    
    # Delete transfer
    db.delete(db_transfer)
    db.commit()
    
    return {"message": "Transfer deleted successfully"}

@router.post("/{transfer_id}/add-units")
def add_units_to_transfer(
    transfer_id: int,
    unit_ids: List[int],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    db_transfer = db.query(models.Transfer).filter(models.Transfer.id == transfer_id).first()
    if not db_transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    if db_transfer.status != "pending":
        raise HTTPException(status_code=400, detail="Can only add units to pending transfers")
    
    # Validate units
    units = db.query(models.Unit).filter(models.Unit.id.in_(unit_ids)).all()
    if len(units) != len(unit_ids):
        raise HTTPException(status_code=400, detail="Some units not found")
    
    # Check if units are already in this transfer
    existing_units = db.query(models.TransferUnit).filter(
        and_(
            models.TransferUnit.transfer_id == transfer_id,
            models.TransferUnit.unit_id.in_(unit_ids)
        )
    ).all()
    
    if existing_units:
        raise HTTPException(status_code=400, detail="Some units are already in this transfer")
    
    # Add units to transfer
    for unit_id in unit_ids:
        unit = db.query(models.Unit).filter(models.Unit.id == unit_id).first()
        
        # Validate unit location and status
        if unit.current_location_id != db_transfer.from_location_id:
            raise HTTPException(
                status_code=400,
                detail=f"Unit {unit.engine_number} is not at the source location"
            )
        
        if unit.status not in [UnitStatus.AVAILABLE, UnitStatus.RESERVED]:
            raise HTTPException(
                status_code=400,
                detail=f"Unit {unit.engine_number} is not available for transfer"
            )
        
        # Add to transfer
        transfer_unit = models.TransferUnit(
            transfer_id=transfer_id,
            unit_id=unit_id
        )
        db.add(transfer_unit)
        
        # Update unit status
        unit.status = UnitStatus.IN_TRANSIT
    
    # Update transfer total
    db_transfer.total_units += len(unit_ids)
    
    db.commit()
    
    return {"message": f"Added {len(unit_ids)} units to transfer"}

@router.delete("/{transfer_id}/units/{unit_id}")
def remove_unit_from_transfer(
    transfer_id: int,
    unit_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER, UserRole.OPERATOR]))
):
    db_transfer = db.query(models.Transfer).filter(models.Transfer.id == transfer_id).first()
    if not db_transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")
    
    if db_transfer.status != "pending":
        raise HTTPException(status_code=400, detail="Can only remove units from pending transfers")
    
    # Find transfer unit
    transfer_unit = db.query(models.TransferUnit).filter(
        and_(
            models.TransferUnit.transfer_id == transfer_id,
            models.TransferUnit.unit_id == unit_id
        )
    ).first()
    
    if not transfer_unit:
        raise HTTPException(status_code=404, detail="Unit not found in this transfer")
    
    # Reset unit status
    unit = db.query(models.Unit).filter(models.Unit.id == unit_id).first()
    unit.status = UnitStatus.AVAILABLE
    
    # Remove from transfer
    db.delete(transfer_unit)
    
    # Update transfer total
    db_transfer.total_units -= 1
    
    db.commit()
    
    return {"message": "Unit removed from transfer"}
