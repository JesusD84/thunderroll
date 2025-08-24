
"""Unit management service."""

import json
from datetime import datetime
from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.unit import Unit, UnitStatus
from app.models.unit_event import UnitEvent, EventType
from app.models.location import Location, LocationType
from app.models.user import User
from app.schemas.unit import UnitCreate, UnitUpdate, UnitFilter, UnitIdentification


class UnitService:
    """Service for unit operations."""
    
    @staticmethod
    async def create_unit(
        db: AsyncSession,
        unit_data: UnitCreate,
        location_id: int,
        user_id: int
    ) -> Unit:
        """Create a new unit."""
        # Create unit
        unit = Unit(
            brand=unit_data.brand,
            model=unit_data.model,
            color=unit_data.color,
            supplier_invoice=unit_data.supplier_invoice,
            shipment_id=unit_data.shipment_id,
            location_id=location_id,
            notes=unit_data.notes,
            last_updated_by_id=user_id
        )
        
        db.add(unit)
        await db.flush()  # Get ID before commit
        
        # Create audit event
        await UnitService._create_event(
            db=db,
            unit_id=unit.id,
            event_type=EventType.CREATED,
            user_id=user_id,
            after=UnitService._unit_to_dict(unit),
            reason="Unit created manually"
        )
        
        await db.commit()
        await db.refresh(unit)
        
        return unit
    
    @staticmethod
    async def get_units(
        db: AsyncSession,
        filters: UnitFilter,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Unit], int]:
        """Get units with filtering and pagination."""
        query = select(Unit).options(
            selectinload(Unit.location),
            selectinload(Unit.assigned_branch),
            selectinload(Unit.shipment),
            selectinload(Unit.last_updated_by)
        )
        
        # Apply filters
        conditions = []
        
        if filters.status:
            conditions.append(Unit.status == filters.status)
        
        if filters.location_id:
            conditions.append(Unit.location_id == filters.location_id)
            
        if filters.shipment_id:
            conditions.append(Unit.shipment_id == filters.shipment_id)
            
        if filters.brand:
            conditions.append(Unit.brand.ilike(f"%{filters.brand}%"))
            
        if filters.model:
            conditions.append(Unit.model.ilike(f"%{filters.model}%"))
            
        if filters.engine_number:
            conditions.append(Unit.engine_number == filters.engine_number)
            
        if filters.chassis_number:
            conditions.append(Unit.chassis_number.ilike(f"%{filters.chassis_number}%"))
            
        if filters.query:
            # General search across multiple fields
            search_conditions = [
                Unit.brand.ilike(f"%{filters.query}%"),
                Unit.model.ilike(f"%{filters.query}%"),
                Unit.color.ilike(f"%{filters.query}%"),
                Unit.chassis_number.ilike(f"%{filters.query}%"),
            ]
            # Try to search by engine number if query is numeric
            try:
                engine_num = int(filters.query)
                search_conditions.append(Unit.engine_number == engine_num)
            except ValueError:
                pass
            
            conditions.append(or_(*search_conditions))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        query = query.offset(skip).limit(limit).order_by(Unit.created_at.desc())
        
        result = await db.execute(query)
        units = result.scalars().all()
        
        return list(units), total
    
    @staticmethod
    async def get_unit_by_id(db: AsyncSession, unit_id: UUID) -> Optional[Unit]:
        """Get unit by ID with all related data."""
        query = select(Unit).options(
            selectinload(Unit.location),
            selectinload(Unit.assigned_branch),
            selectinload(Unit.shipment),
            selectinload(Unit.last_updated_by),
            selectinload(Unit.events).selectinload(UnitEvent.user)
        ).where(Unit.id == unit_id)
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_unit(
        db: AsyncSession,
        unit_id: UUID,
        unit_update: UnitUpdate,
        user_id: int
    ) -> Unit:
        """Update a unit."""
        # Get existing unit
        unit = await UnitService.get_unit_by_id(db, unit_id)
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        # Store before state
        before_state = UnitService._unit_to_dict(unit)
        
        # Update fields
        if unit_update.brand is not None:
            unit.brand = unit_update.brand
        if unit_update.model is not None:
            unit.model = unit_update.model
        if unit_update.color is not None:
            unit.color = unit_update.color
        if unit_update.engine_number is not None:
            unit.engine_number = unit_update.engine_number
        if unit_update.chassis_number is not None:
            unit.chassis_number = unit_update.chassis_number
        if unit_update.notes is not None:
            unit.notes = unit_update.notes
        if unit_update.assigned_branch_id is not None:
            unit.assigned_branch_id = unit_update.assigned_branch_id
        
        unit.last_updated_by_id = user_id
        unit.updated_at = datetime.utcnow()
        
        # Create audit event
        await UnitService._create_event(
            db=db,
            unit_id=unit.id,
            event_type=EventType.ADJUSTED,
            user_id=user_id,
            before=before_state,
            after=UnitService._unit_to_dict(unit),
            reason="Unit updated"
        )
        
        await db.commit()
        await db.refresh(unit)
        
        return unit
    
    @staticmethod
    async def match_identification(
        db: AsyncSession,
        identification: UnitIdentification,
        user_id: int
    ) -> Unit:
        """Match engine and chassis numbers to identify a unit."""
        # Build query
        query = select(Unit).where(
            Unit.status == UnitStatus.EN_BODEGA_NO_IDENTIFICADA
        )
        
        # Optionally filter by shipment
        if identification.shipment_id:
            query = query.where(Unit.shipment_id == identification.shipment_id)
        
        # Look for matching unit (by brand/model/color)
        # For now, we'll find any unidentified unit and assign the numbers
        result = await db.execute(query.limit(1))
        unit = result.scalar_one_or_none()
        
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No unidentified unit found to match"
            )
        
        # Check if numbers are already taken
        engine_check = await db.execute(
            select(Unit).where(Unit.engine_number == identification.engine_number)
        )
        if engine_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Engine number already assigned to another unit"
            )
        
        chassis_check = await db.execute(
            select(Unit).where(Unit.chassis_number == identification.chassis_number)
        )
        if chassis_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chassis number already assigned to another unit"
            )
        
        # Get taller location
        taller_result = await db.execute(
            select(Location).where(Location.type == LocationType.TALLER)
        )
        taller = taller_result.scalar_one_or_none()
        
        if not taller:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Taller location not found"
            )
        
        # Store before state
        before_state = UnitService._unit_to_dict(unit)
        
        # Update unit
        unit.engine_number = identification.engine_number
        unit.chassis_number = identification.chassis_number
        unit.status = UnitStatus.IDENTIFICADA_EN_TALLER
        unit.location_id = taller.id
        unit.last_updated_by_id = user_id
        unit.updated_at = datetime.utcnow()
        
        # Create audit event
        await UnitService._create_event(
            db=db,
            unit_id=unit.id,
            event_type=EventType.IDENTIFIED,
            user_id=user_id,
            before=before_state,
            after=UnitService._unit_to_dict(unit),
            reason=f"Unit identified with engine: {identification.engine_number}, chassis: {identification.chassis_number}"
        )
        
        await db.commit()
        await db.refresh(unit)
        
        return unit
    
    @staticmethod
    async def _create_event(
        db: AsyncSession,
        unit_id: UUID,
        event_type: EventType,
        user_id: int,
        before: dict = None,
        after: dict = None,
        reason: str = None
    ):
        """Create a unit event for audit trail."""
        event = UnitEvent(
            unit_id=unit_id,
            event_type=event_type,
            before=before,
            after=after,
            user_id=user_id,
            reason=reason
        )
        db.add(event)
    
    @staticmethod
    def _unit_to_dict(unit: Unit) -> dict:
        """Convert unit to dictionary for audit trail."""
        return {
            "brand": unit.brand,
            "model": unit.model,
            "color": unit.color,
            "engine_number": unit.engine_number,
            "chassis_number": unit.chassis_number,
            "status": unit.status.value,
            "location_id": unit.location_id,
            "assigned_branch_id": unit.assigned_branch_id,
            "notes": unit.notes
        }
