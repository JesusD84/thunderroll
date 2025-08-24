
"""Sales endpoints."""

from uuid import UUID
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_ventas
from app.schemas.sale import Sale, SaleCreate
from app.services.sale import SaleService

router = APIRouter()


@router.post("/{unit_id}/sell", response_model=Sale)
async def sell_unit(
    unit_id: UUID,
    sale_data: SaleCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(require_ventas)
):
    """
    Sell a unit.
    
    Unit must be in EN_SUCURSAL_DISPONIBLE or RESERVADA status.
    Creates sale record and marks unit as VENDIDA.
    """
    
    # Override user_id and unit_id from path/auth
    sale_data.unit_id = unit_id
    sale_data.sold_by_id = current_user.id
    
    sale = await SaleService.sell_unit(
        db=db,
        unit_id=unit_id,
        sale_data=sale_data,
        user_id=current_user.id
    )
    
    return sale
