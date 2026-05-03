from datetime import datetime, UTC
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Transfer, TransferStatus, Unit, UnitStatus
from app.models.schemas import TransferCreate as UnitTransferCreate
from app.repositories.location_repository import LocationRepository
from app.repositories.transfer_repository import TransferRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.user_repository import UserRepository
from app.schemas.transfer import TransferCreate, TransferFilters, TransferUpdate, TransferStats


class TransferService:

    @staticmethod
    def get_transfers(db: Session, filters: TransferFilters, skip: int, limit: int) -> list[Transfer]:
        return TransferRepository.get_transfers(db, filters, skip, limit)

    @staticmethod
    def get_transfer_by_id(db: Session, transfer_id: int) -> Transfer:
        transfer = TransferRepository.get_transfer(db, transfer_id)
        if not transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")
        return transfer

    @staticmethod
    def create_transfer(db: Session, transfer_data: TransferCreate) -> Transfer:
        TransferService._validate_relations(db, transfer_data)
        payload = transfer_data.model_copy(deep=True)
        if payload.status == TransferStatus.RECEIVED and payload.received_at is None:
            payload.received_at = datetime.now(UTC)

        # Update unit status based on transfer
        unit = UnitRepository.get_unit(db, transfer_data.unit_id)
        if unit and transfer_data.destination_location_id:
            unit.status = UnitStatus.IN_TRANSIT
            db.commit()

        return TransferRepository.create_transfer(db, payload)

    @staticmethod
    def transfer_unit_with_status_update(
        db: Session,
        unit_id: int,
        transfer_data: UnitTransferCreate,
        user_id: int,
    ) -> Unit:
        unit = UnitRepository.get_unit(db, unit_id)
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

        from_location_id = getattr(transfer_data, "from_location_id", None)
        to_location_id = getattr(transfer_data, "to_location_id", None)
        unit_ids = getattr(transfer_data, "unit_ids", None)

        if unit_ids is not None and unit_id not in unit_ids:
            raise HTTPException(status_code=400, detail="unit_id path does not match transfer payload")

        if from_location_id is None:
            from_location_id = unit.current_location_id

        if from_location_id and to_location_id and from_location_id == to_location_id:
            raise HTTPException(status_code=400, detail="Origin and destination locations must be different")

        if to_location_id is not None:
            transfer_status = TransferStatus.IN_TRANSIT
            unit.status = UnitStatus.IN_TRANSIT
        else:
            transfer_status = TransferStatus.RECEIVED
            unit.status = UnitStatus.SOLD
            unit.sold_date = datetime.now(UTC)

        db.commit()
        db.refresh(unit)

        TransferRepository.create_unit_transfer(
            db=db,
            unit_id=unit_id,
            dispatched_by_id=user_id,
            origin_location_id=from_location_id,
            destination_location_id=to_location_id,
            status=transfer_status,
            dispatched_at=datetime.now(UTC),
            received_at=datetime.now(UTC) if transfer_status == TransferStatus.RECEIVED else None,
        )

        return UnitRepository.get_unit(db, unit.id)

    @staticmethod
    def create_unit_transfer_record(
        db: Session,
        unit_id: int,
        user_id: int,
        origin_location_id: int | None = None,
        destination_location_id: int | None = None,
        status: TransferStatus = TransferStatus.PENDING,
        dispatched_at: datetime | None = None,
        received_at: datetime | None = None,
    ) -> Transfer:
        return TransferRepository.create_unit_transfer(
            db=db,
            unit_id=unit_id,
            dispatched_by_id=user_id,
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            status=status,
            dispatched_at=dispatched_at,
            received_at=received_at,
        )

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
    def update_transfer(db: Session, transfer_id: int, transfer_update: TransferUpdate) -> Transfer:
        db_transfer = TransferRepository.get_transfer(db, transfer_id)
        if not db_transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")

        merged_data = TransferCreate(
            unit_id=transfer_update.unit_id if transfer_update.unit_id is not None else db_transfer.unit_id,
            dispatched_by_id=transfer_update.dispatched_by_id if transfer_update.dispatched_by_id is not None else db_transfer.dispatched_by_id,
            received_by_id=transfer_update.received_by_id if transfer_update.received_by_id is not None else db_transfer.received_by_id,
            origin_location_id=transfer_update.origin_location_id if transfer_update.origin_location_id is not None else db_transfer.origin_location_id,
            destination_location_id=transfer_update.destination_location_id if transfer_update.destination_location_id is not None else db_transfer.destination_location_id,
            status=transfer_update.status if transfer_update.status is not None else db_transfer.status,
            dispatched_at=transfer_update.dispatched_at if transfer_update.dispatched_at is not None else db_transfer.dispatched_at,
            received_at=transfer_update.received_at if transfer_update.received_at is not None else db_transfer.received_at,
        )
        TransferService._validate_relations(db, merged_data)

        update_payload = transfer_update.model_copy(deep=True)
        if update_payload.status == TransferStatus.RECEIVED and update_payload.received_at is None:
            update_payload.received_at = datetime.now(UTC)

        # When marking as RECEIVED, update unit status and location
        if update_payload.status == TransferStatus.RECEIVED:
            unit = UnitRepository.get_unit(db, db_transfer.unit_id)
            if unit:
                unit.status = UnitStatus.AVAILABLE
                dest = merged_data.destination_location_id
                if dest:
                    unit.current_location_id = dest
                db.commit()

        return TransferRepository.update_transfer(db, db_transfer, update_payload)

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
        pending_transfers = TransferRepository.count_transfers_by_status(db, TransferStatus.PENDING)
        in_transit_transfers = TransferRepository.count_transfers_by_status(db, TransferStatus.IN_TRANSIT)
        received_transfers = TransferRepository.count_transfers_by_status(db, TransferStatus.RECEIVED)
        cancelled_transfers = TransferRepository.count_transfers_by_status(db, TransferStatus.CANCELLED)
        recent_transfers = TransferRepository.get_recent_transfers(db)

        return TransferStats(
            total_transfers=total_transfers,
            pending_transfers=pending_transfers,
            in_transit_transfers=in_transit_transfers,
            received_transfers=received_transfers,
            cancelled=cancelled_transfers,
            recent_transfers=recent_transfers,
        )

    @staticmethod
    def _validate_relations(db: Session, transfer_data: TransferCreate) -> None:
        if not UnitRepository.get_unit(db, transfer_data.unit_id):
            raise HTTPException(status_code=404, detail="Unit not found")

        if transfer_data.dispatched_by_id and not UserRepository.get_user_by_id(db, transfer_data.dispatched_by_id):
            raise HTTPException(status_code=404, detail="Dispatching user not found")

        if transfer_data.received_by_id and not UserRepository.get_user_by_id(db, transfer_data.received_by_id):
            raise HTTPException(status_code=404, detail="Receiving user not found")

        if transfer_data.origin_location_id and not LocationRepository.get_location(db, transfer_data.origin_location_id):
            raise HTTPException(status_code=404, detail="Origin location not found")

        if transfer_data.destination_location_id and not LocationRepository.get_location(db, transfer_data.destination_location_id):
            raise HTTPException(status_code=404, detail="Destination location not found")

        if (
            transfer_data.origin_location_id
            and transfer_data.destination_location_id
            and transfer_data.origin_location_id == transfer_data.destination_location_id
        ):
            raise HTTPException(status_code=400, detail="Origin and destination locations must be different")
