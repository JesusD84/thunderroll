"""The one and only way to sell a unit.

Every sale goes through here: the sell endpoint, a transfer without a
destination, and anything else that wants to mark a unit as sold. Because
there is a single door, a sale always leaves the same trace: the unit is
marked SOLD with the server clock, and the history keeps the record of it.
"""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import TransferStatus, Unit, UnitStatus
from app.repositories.transfer_repository import TransferRepository
from app.repositories.unit_repository import UnitRepository
from app.services import lifecycle


class SaleService:
    """Sells units and writes the trail of the sale."""

    @staticmethod
    def sell_unit(
        db: Session,
        unit_id: int,
        actor_id: int,
        notes: str | None = None,
    ) -> Unit:
        """Sell a unit: mark it SOLD and record the sale in the history.

        The unit is locked for the rest of the transaction, so two sales of
        the same unit cannot both go through: the second one finds the unit
        already sold and is rejected with 409.
        """
        unit = UnitRepository.get_unit_for_update(db, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        if unit.status == UnitStatus.SOLD:
            raise HTTPException(status_code=409, detail="Unit is already sold")

        active_transfer = TransferRepository.get_active_transfer_by_unit(db, unit_id)
        if active_transfer:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Unit has an active transfer; the transfer has to be closed "
                    "before the unit can be sold"
                ),
            )

        try:
            lifecycle.ensure_unit_transition(unit.status, UnitStatus.SOLD)
        except lifecycle.InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        now = datetime.now(UTC)

        unit.status = UnitStatus.SOLD
        unit.sold_date = now
        if notes and notes.strip():
            sale_note = f"Venta: {notes.strip()}"
            unit.notes = f"{unit.notes}\n{sale_note}" if unit.notes else sale_note

        # The sale belongs to the history: a closed transfer with no
        # destination, written in the same transaction as the unit change.
        transfer = TransferRepository.build_transfer(
            unit_id=unit.id,
            status=TransferStatus.RECEIVED,
            origin_location_id=unit.current_location_id,
            destination_location_id=None,
            dispatched_by_id=actor_id,
            received_by_id=actor_id,
            dispatched_at=now,
            received_at=now,
        )
        db.add(transfer)
        db.commit()
        db.refresh(unit)

        return unit
