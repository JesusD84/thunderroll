"""Transfers between locations, and the state changes they cause.

The rules of the lifecycle live in ``app.services.lifecycle``; this module
applies them. Two invariants shape every method here:

* a unit and its transfer are written in a **single transaction**, so the
  trail never shows a unit in transit without the transfer that says so;
* the unit row is **locked** (``SELECT ... FOR UPDATE`` on PostgreSQL) while
  it is being checked and written, so two concurrent dispatches of the same
  unit cannot both pass the checks.
"""

from datetime import UTC, datetime

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.models import Transfer, TransferStatus, Unit, UnitStatus
from app.repositories.location_repository import LocationRepository
from app.repositories.transfer_repository import TransferRepository
from app.repositories.unit_repository import UnitRepository
from app.schemas.transfer import (
    TransferCreate,
    TransferFilters,
    TransferReceiveUpdate,
    TransferStats,
    TransferUpdate,
    UnitTransferRequest,
)
from app.services import lifecycle
from app.services.sale_service import SaleService


class TransferService:
    @staticmethod
    def get_transfers(
        db: Session, filters: TransferFilters, skip: int, limit: int
    ) -> list[Transfer]:
        return TransferRepository.get_transfers(db, filters, skip, limit)

    @staticmethod
    def get_transfer_by_id(db: Session, transfer_id: int) -> Transfer:
        transfer = TransferRepository.get_transfer(db, transfer_id)
        if not transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")
        return transfer

    @staticmethod
    def create_transfer(
        db: Session, transfer_data: TransferCreate, actor_id: int
    ) -> Transfer:
        """Dispatch a unit to another location (POST /transfers/).

        The state of the transfer is the server's: a dispatch always starts
        as PENDING. The state of the unit comes out of the transfer, so a
        dispatch leaves the unit IN_TRANSIT towards the destination.
        """
        unit = UnitRepository.get_unit_for_update(db, transfer_data.unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        if unit.status == UnitStatus.SOLD:
            raise HTTPException(
                status_code=409, detail="A sold unit cannot be dispatched"
            )

        origin_location_id = transfer_data.origin_location_id or unit.current_location_id
        if origin_location_id != unit.current_location_id:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Unit {unit.id} is not at location {origin_location_id}: "
                    f"it is at location {unit.current_location_id}"
                ),
            )

        destination_location_id = transfer_data.destination_location_id
        if destination_location_id is None:
            raise HTTPException(
                status_code=422, detail="destination_location_id is required"
            )
        if destination_location_id == origin_location_id:
            raise HTTPException(
                status_code=400,
                detail="Origin and destination locations must be different",
            )
        if not LocationRepository.get_location(db, destination_location_id):
            raise HTTPException(status_code=404, detail="Destination location not found")

        TransferService._ensure_no_active_transfer(db, unit.id)

        transfer_status = TransferStatus.PENDING
        new_unit_status = lifecycle.unit_status_for_transfer(transfer_status)
        TransferService._ensure_unit_transition(unit.status, new_unit_status)

        now = datetime.now(UTC)
        unit.status = new_unit_status
        transfer = TransferRepository.build_transfer(
            unit_id=unit.id,
            status=transfer_status,
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            dispatched_by_id=actor_id,
            dispatched_at=now,
        )
        db.add(transfer)
        db.commit()
        db.refresh(transfer)

        return transfer

    @staticmethod
    def restrict_update_for_operator(transfer: TransferUpdate) -> TransferUpdate:
        """Narrow an Operator's update payload to confirming the arrival.

        Rewriting the dispatch record (who dispatched the unit, when, from
        where to where) would falsify the traceability trail, so an Operator
        may only confirm the arrival. The payload is re-validated against
        ``TransferReceiveUpdate``: anything else is rejected with 422.
        """
        try:
            receive = TransferReceiveUpdate.model_validate(
                transfer.model_dump(exclude_unset=True)
            )
        except ValidationError as exc:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Operators can only confirm the arrival of a transfer "
                    "(status=RECEIVED)."
                ),
            ) from exc

        return TransferUpdate(status=receive.status)

    @staticmethod
    def transfer_unit_with_status_update(
        db: Session,
        unit_id: int,
        transfer_data: UnitTransferRequest,
        user_id: int,
    ) -> Unit:
        """Dispatch a unit from its detail page (POST /transfers/unit/{id}).

        Without a destination this is a sale, and it goes through the sale
        service: there is only one way to sell a unit.
        """
        unit = UnitRepository.get_unit_for_update(db, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        if unit.status == UnitStatus.SOLD:
            raise HTTPException(
                status_code=409, detail="A sold unit cannot be dispatched"
            )

        if unit.status == UnitStatus.IN_TRANSIT:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Unit is already in transit: the active transfer has to be "
                    "closed before the unit can be dispatched again"
                ),
            )

        origin_location_id = transfer_data.from_location_id or unit.current_location_id
        if origin_location_id != unit.current_location_id:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Unit {unit.id} is not at location {origin_location_id}: "
                    f"it is at location {unit.current_location_id}"
                ),
            )

        destination_location_id = transfer_data.to_location_id
        if destination_location_id is None:
            # No destination: this is a sale.
            return SaleService.sell_unit(db, unit_id, user_id, transfer_data.notes)

        if destination_location_id == origin_location_id:
            raise HTTPException(
                status_code=400,
                detail="Origin and destination locations must be different",
            )
        if not LocationRepository.get_location(db, destination_location_id):
            raise HTTPException(status_code=404, detail="Destination location not found")

        TransferService._ensure_no_active_transfer(db, unit.id)

        transfer_status = TransferStatus.PENDING
        new_unit_status = lifecycle.unit_status_for_transfer(transfer_status)
        TransferService._ensure_unit_transition(unit.status, new_unit_status)

        now = datetime.now(UTC)
        unit.status = new_unit_status
        transfer = TransferRepository.build_transfer(
            unit_id=unit.id,
            status=transfer_status,
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            dispatched_by_id=user_id,
            dispatched_at=now,
        )
        db.add(transfer)
        db.commit()
        db.refresh(unit)

        return unit

    @staticmethod
    def get_active_transfer_for_unit(db: Session, unit_id: int) -> Transfer:
        unit = UnitRepository.get_unit(db, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        transfer = TransferRepository.get_active_transfer_by_unit(db, unit_id)
        if not transfer:
            raise HTTPException(status_code=404, detail="No active transfer found")

        return transfer

    @staticmethod
    def update_transfer(
        db: Session,
        transfer_id: int,
        transfer_update: TransferUpdate,
        actor_id: int,
    ) -> Transfer:
        """Close a transfer: RECEIVED (the unit arrived) or CANCELLED.

        Only the status may change. The unit follows the transfer: receiving
        it leaves the unit AVAILABLE at the destination, cancelling it brings
        the unit back to AVAILABLE at the origin. Both happen in a single
        transaction, together with the transfer itself.
        """
        db_transfer = TransferRepository.get_transfer(db, transfer_id)
        if not db_transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")

        target_status = transfer_update.status
        try:
            lifecycle.ensure_transfer_transition(db_transfer.status, target_status)
        except lifecycle.InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        unit = UnitRepository.get_unit_for_update(db, db_transfer.unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        now = datetime.now(UTC)

        if target_status == TransferStatus.RECEIVED:
            if unit.status == UnitStatus.SOLD:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "The unit was sold: a sold unit cannot be received "
                        "again"
                    ),
                )
            destination_location_id = db_transfer.destination_location_id
            if destination_location_id is None:
                raise HTTPException(
                    status_code=409,
                    detail="The transfer has no destination to receive the unit at",
                )
            unit.status = UnitStatus.AVAILABLE
            unit.current_location_id = destination_location_id
        elif target_status == TransferStatus.CANCELLED:
            unit.status = UnitStatus.AVAILABLE
            origin_location_id = (
                db_transfer.origin_location_id or unit.current_location_id
            )
            unit.current_location_id = origin_location_id

        db_transfer.status = target_status
        db_transfer.received_by_id = actor_id
        db_transfer.received_at = now
        db.commit()
        db.refresh(db_transfer)

        return db_transfer

    @staticmethod
    def delete_transfer(db: Session, transfer_id: int) -> dict:
        db_transfer = TransferRepository.get_transfer(db, transfer_id)
        if not db_transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")
        TransferRepository.delete_transfer(db, db_transfer)
        return {"message": "Transfer deleted successfully"}

    @staticmethod
    def get_transfer_stats(db: Session) -> TransferStats:
        total_transfers = TransferRepository.count_transfers(db)
        pending_transfers = TransferRepository.count_transfers_by_status(
            db, TransferStatus.PENDING
        )
        in_transit_transfers = TransferRepository.count_transfers_by_status(
            db, TransferStatus.IN_TRANSIT
        )
        received_transfers = TransferRepository.count_transfers_by_status(
            db, TransferStatus.RECEIVED
        )
        cancelled_transfers = TransferRepository.count_transfers_by_status(
            db, TransferStatus.CANCELLED
        )
        recent_transfers = TransferRepository.get_recent_transfers(db)

        return TransferStats(
            total_transfers=total_transfers,
            pending_transfers=pending_transfers,
            in_transit_transfers=in_transit_transfers,
            received_transfers=received_transfers,
            cancelled=cancelled_transfers,
            recent_transfers=recent_transfers,
        )

    # ------------------------------------------------------------------
    # The rules the services above share
    # ------------------------------------------------------------------

    @staticmethod
    def _ensure_no_active_transfer(db: Session, unit_id: int) -> None:
        """A unit may have at most one active transfer at a time."""
        active_transfer = TransferRepository.get_active_transfer_by_unit(db, unit_id)
        if active_transfer:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Unit {unit_id} already has an active transfer "
                    f"(id {active_transfer.id}): close it before dispatching "
                    "the unit again"
                ),
            )

    @staticmethod
    def _ensure_unit_transition(current: UnitStatus, target: UnitStatus) -> None:
        """The unit may only change into a state the lifecycle allows."""
        try:
            lifecycle.ensure_unit_transition(current, target)
        except lifecycle.InvalidTransition as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
