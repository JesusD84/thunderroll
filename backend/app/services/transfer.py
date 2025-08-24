
"""Transfer service for unit movements between locations."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.unit import Unit, UnitStatus
from app.models.location import Location
from app.models.transfer import Transfer, TransferStatus
from app.models.unit_event import EventType
from app.schemas.transfer import TransferCreate, TransferReceive
from app.services.unit import UnitService


class TransferService:
    """Service for managing unit transfers between locations."""
    
    @staticmethod
    async def create_transfer(
        db: AsyncSession,
        transfer_data: TransferCreate,
        user_id: int
    ) -> Transfer:
        """Create a new transfer request."""
        
        # Validate unit exists and is transferable
        unit = await UnitService.get_unit_by_id(db, transfer_data.unit_id)
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        # Check if unit is in the from_location
        if unit.location_id != transfer_data.from_location_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unit is not currently in the specified from_location"
            )
        
        # Validate locations exist
        from_location = await TransferService._get_location(db, transfer_data.from_location_id)
        to_location = await TransferService._get_location(db, transfer_data.to_location_id)
        
        if not from_location or not to_location:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or both locations not found"
            )
        
        # Check if there's already a pending transfer for this unit
        existing_transfer = await db.execute(
            select(Transfer).where(
                and_(
                    Transfer.unit_id == transfer_data.unit_id,
                    Transfer.status.in_([TransferStatus.PENDING, TransferStatus.IN_TRANSIT])
                )
            )
        )
        
        if existing_transfer.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unit already has a pending transfer"
            )
        
        # Determine new unit status based on transfer
        new_status = TransferService._determine_transfer_status(
            unit.status, 
            from_location.type, 
            to_location.type
        )
        
        # Store before state
        before_state = UnitService._unit_to_dict(unit)
        
        # Update unit status
        unit.status = new_status
        unit.last_updated_by_id = user_id
        unit.updated_at = datetime.utcnow()
        
        # Create transfer record
        transfer = Transfer(
            unit_id=transfer_data.unit_id,
            from_location_id=transfer_data.from_location_id,
            to_location_id=transfer_data.to_location_id,
            eta=transfer_data.eta,
            created_by_id=user_id,
            status=TransferStatus.IN_TRANSIT,
            reason=transfer_data.reason
        )
        
        db.add(transfer)
        await db.flush()  # Get transfer ID
        
        # Create audit event
        await UnitService._create_event(
            db=db,
            unit_id=unit.id,
            event_type=EventType.TRANSFER_INITIATED,
            user_id=user_id,
            before=before_state,
            after=UnitService._unit_to_dict(unit),
            reason=f"Transfer initiated from {from_location.name} to {to_location.name}"
        )
        
        await db.commit()
        await db.refresh(transfer)
        
        return transfer
    
    @staticmethod
    async def receive_transfer(
        db: AsyncSession,
        transfer_id: int,
        receive_data: TransferReceive
    ) -> Transfer:
        """Receive a transfer at destination."""
        
        # Get transfer with related data
        result = await db.execute(
            select(Transfer).options(
                selectinload(Transfer.unit),
                selectinload(Transfer.to_location)
            ).where(Transfer.id == transfer_id)
        )
        transfer = result.scalar_one_or_none()
        
        if not transfer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Transfer not found"
            )
        
        if transfer.status != TransferStatus.IN_TRANSIT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transfer is not in transit (current status: {transfer.status})"
            )
        
        # Store before state
        before_state = UnitService._unit_to_dict(transfer.unit)
        
        # Update unit location and status
        transfer.unit.location_id = transfer.to_location_id
        transfer.unit.status = TransferService._determine_arrival_status(
            transfer.to_location.type
        )
        transfer.unit.last_updated_by_id = receive_data.received_by_id
        transfer.unit.updated_at = datetime.utcnow()
        
        # Update transfer
        transfer.status = TransferStatus.RECEIVED
        transfer.received_by_id = receive_data.received_by_id
        transfer.received_at = datetime.utcnow()
        
        # Create audit event
        await UnitService._create_event(
            db=db,
            unit_id=transfer.unit.id,
            event_type=EventType.TRANSFER_RECEIVED,
            user_id=receive_data.received_by_id,
            before=before_state,
            after=UnitService._unit_to_dict(transfer.unit),
            reason=f"Transfer received at {transfer.to_location.name}"
        )
        
        await db.commit()
        await db.refresh(transfer)
        
        return transfer
    
    @staticmethod
    async def get_transfers(
        db: AsyncSession,
        status: Optional[TransferStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Transfer]:
        """Get transfers with optional filtering."""
        
        query = select(Transfer).options(
            selectinload(Transfer.unit),
            selectinload(Transfer.from_location),
            selectinload(Transfer.to_location),
            selectinload(Transfer.created_by),
            selectinload(Transfer.received_by)
        )
        
        if status:
            query = query.where(Transfer.status == status)
        
        query = query.offset(skip).limit(limit).order_by(Transfer.created_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def _get_location(db: AsyncSession, location_id: int) -> Optional[Location]:
        """Get location by ID."""
        result = await db.execute(
            select(Location).where(Location.id == location_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    def _determine_transfer_status(
        current_status: UnitStatus,
        from_type: str,
        to_type: str
    ) -> UnitStatus:
        """Determine unit status when transfer is initiated."""
        
        # Taller to Sucursal
        if from_type == "TALLER" and to_type == "SUCURSAL":
            return UnitStatus.EN_TRANSITO_TALLER_SUCURSAL
        
        # Sucursal to Sucursal
        if from_type == "SUCURSAL" and to_type == "SUCURSAL":
            return UnitStatus.EN_TRANSITO_SUCURSAL_SUCURSAL
        
        # For any other combination, return current status
        # (could be extended for other transfer types)
        return current_status
    
    @staticmethod
    def _determine_arrival_status(location_type: str) -> UnitStatus:
        """Determine unit status when transfer is received."""
        
        if location_type == "SUCURSAL":
            return UnitStatus.EN_SUCURSAL_DISPONIBLE
        elif location_type == "TALLER":
            return UnitStatus.IDENTIFICADA_EN_TALLER
        elif location_type == "BODEGA":
            return UnitStatus.EN_BODEGA_NO_IDENTIFICADA
        
        # Default fallback
        return UnitStatus.EN_SUCURSAL_DISPONIBLE
