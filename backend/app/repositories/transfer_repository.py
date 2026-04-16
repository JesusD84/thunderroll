from sqlalchemy.orm import Session

from app.models.models import Transfer
from app.schemas.transfer import TransferCreate, TransferFilters, TransferUpdate


class TransferRepository:

    @staticmethod
    def get_transfers(db: Session, filters: TransferFilters, skip: int, limit: int) -> list[Transfer]:
        query = db.query(Transfer)

        if filters.unit_id:
            query = query.filter(Transfer.unit_id == filters.unit_id)
        if filters.status:
            query = query.filter(Transfer.status == filters.status)
        if filters.origin_location_id:
            query = query.filter(Transfer.origin_location_id == filters.origin_location_id)
        if filters.destination_location_id:
            query = query.filter(Transfer.destination_location_id == filters.destination_location_id)
        if filters.dispatched_by_id:
            query = query.filter(Transfer.dispatched_by_id == filters.dispatched_by_id)
        if filters.received_by_id:
            query = query.filter(Transfer.received_by_id == filters.received_by_id)

        return query.order_by(Transfer.id.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_transfer(db: Session, transfer_id: int) -> Transfer | None:
        return db.query(Transfer).filter(Transfer.id == transfer_id).first()

    @staticmethod
    def create_transfer(db: Session, transfer_data: TransferCreate) -> Transfer:
        db_transfer = Transfer(**transfer_data.model_dump())
        db.add(db_transfer)
        db.commit()
        db.refresh(db_transfer)
        return db_transfer

    @staticmethod
    def update_transfer(db: Session, db_transfer: Transfer, transfer_update: TransferUpdate) -> Transfer:
        update_data = transfer_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_transfer, field, value)
        db.commit()
        db.refresh(db_transfer)
        return db_transfer

    @staticmethod
    def delete_transfer(db: Session, db_transfer: Transfer) -> None:
        db.delete(db_transfer)
        db.commit()
