from datetime import datetime
from sqlalchemy.orm import Session, selectinload

from app.models.models import Transfer, TransferStatus
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

    @staticmethod
    def count_transfers(db: Session) -> int:
        return db.query(Transfer).count()

    @staticmethod
    def count_transfers_by_status(db: Session, status: TransferStatus) -> int:
        return db.query(Transfer).filter(Transfer.status == status).count()

    @staticmethod
    def get_recent_transfers(db: Session, limit: int = 10) -> list[Transfer]:
        return db.query(Transfer).order_by(Transfer.dispatched_at.desc()).limit(limit).all()

    @staticmethod
    def create_unit_transfer(
        db: Session,
        unit_id: int,
        dispatched_by_id: int,
        origin_location_id: int | None = None,
        destination_location_id: int | None = None,
        status: TransferStatus = TransferStatus.PENDING,
        dispatched_at: datetime | None = None,
        received_at: datetime | None = None,
    ) -> Transfer:
        db_transfer = Transfer(
            unit_id=unit_id,
            dispatched_by_id=dispatched_by_id,
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            status=status,
            dispatched_at=dispatched_at,
            received_at=received_at,
        )
        db.add(db_transfer)
        db.commit()
        db.refresh(db_transfer)
        return db_transfer

    @staticmethod
    def get_active_transfer_by_unit(db: Session, unit_id: int) -> Transfer | None:
        return (
            db.query(Transfer)
            .options(
                selectinload(Transfer.dispatched_by),
                selectinload(Transfer.received_by),
                selectinload(Transfer.origin_location),
                selectinload(Transfer.destination_location),
            )
            .filter(
                Transfer.unit_id == unit_id,
                Transfer.status.in_([TransferStatus.PENDING, TransferStatus.IN_TRANSIT]),
            )
            .order_by(Transfer.dispatched_at.desc())
            .first()
        )
