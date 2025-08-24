
"""Sale service for selling units."""

from datetime import datetime
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from app.models.unit import Unit, UnitStatus
from app.models.sale import Sale
from app.models.unit_event import EventType
from app.schemas.sale import SaleCreate
from app.services.unit import UnitService


class SaleService:
    """Service for managing unit sales."""
    
    @staticmethod
    async def sell_unit(
        db: AsyncSession,
        unit_id: UUID,
        sale_data: SaleCreate,
        user_id: int
    ) -> Sale:
        """Sell a unit."""
        
        # Get unit
        unit = await UnitService.get_unit_by_id(db, unit_id)
        if not unit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Unit not found"
            )
        
        # Validate unit can be sold
        if unit.status not in [UnitStatus.EN_SUCURSAL_DISPONIBLE, UnitStatus.RESERVADA]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unit cannot be sold in current status: {unit.status}"
            )
        
        # Check if unit is already sold
        existing_sale = await db.execute(
            select(Sale).where(Sale.unit_id == unit_id)
        )
        if existing_sale.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unit is already sold"
            )
        
        # Check if receipt number is unique
        existing_receipt = await db.execute(
            select(Sale).where(Sale.receipt == sale_data.receipt)
        )
        if existing_receipt.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Receipt number already exists"
            )
        
        # Store before state
        before_state = UnitService._unit_to_dict(unit)
        
        # Update unit status
        unit.status = UnitStatus.VENDIDA
        unit.last_updated_by_id = user_id
        unit.updated_at = datetime.utcnow()
        
        # Create sale record
        sale = Sale(
            unit_id=unit_id,
            receipt=sale_data.receipt,
            sold_by_id=sale_data.sold_by_id,
            branch_id=sale_data.branch_id,
            sold_at=sale_data.sold_at or datetime.utcnow(),
            customer_name=sale_data.customer_name
        )
        
        db.add(sale)
        await db.flush()
        
        # Create audit event
        await UnitService._create_event(
            db=db,
            unit_id=unit.id,
            event_type=EventType.SOLD,
            user_id=user_id,
            before=before_state,
            after=UnitService._unit_to_dict(unit),
            reason=f"Unit sold - Receipt: {sale_data.receipt}"
        )
        
        await db.commit()
        await db.refresh(sale)
        
        return sale
