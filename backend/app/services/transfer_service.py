from datetime import datetime, UTC
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.models import Transfer, TransferStatus
from app.repositories.location_repository import LocationRepository
from app.repositories.transfer_repository import TransferRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.user_repository import UserRepository
from app.schemas.transfer import TransferCreate, TransferFilters, TransferUpdate


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
        return TransferRepository.create_transfer(db, payload)

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

        return TransferRepository.update_transfer(db, db_transfer, update_payload)

    @staticmethod
    def delete_transfer(db: Session, transfer_id: int) -> dict:
        db_transfer = TransferRepository.get_transfer(db, transfer_id)
        if not db_transfer:
            raise HTTPException(status_code=404, detail="Transfer not found")
        TransferRepository.delete_transfer(db, db_transfer)
        return {"message": "Transfer deleted successfully"}

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
