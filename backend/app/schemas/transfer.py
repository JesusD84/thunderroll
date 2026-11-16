from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import TransferStatus


class TransferBase(BaseModel):
    unit_id: int = Field(..., gt=0)
    dispatched_by_id: int | None = Field(None, gt=0)
    received_by_id: int | None = Field(None, gt=0)
    origin_location_id: int | None = Field(None, gt=0)
    destination_location_id: int | None = Field(None, gt=0)
    status: TransferStatus = TransferStatus.PENDING
    dispatched_at: datetime | None = None
    received_at: datetime | None = None


class TransferCreate(TransferBase):
    """Dispatch payload (POST /transfers/).

    ``extra="forbid"``: only the fields declared here are accepted.
    """

    model_config = ConfigDict(extra="forbid")


class TransferDispatchCreate(BaseModel):
    """Payload an Operator may send to POST /transfers/.

    The Operator role dispatches units; it does not author the dispatch
    record. ``dispatched_by_id``/``dispatched_at`` (who sent it, when) and
    the reception fields belong to the server, so they are not part of this
    schema and ``extra="forbid"`` rejects them with 422.
    """

    model_config = ConfigDict(extra="forbid")

    unit_id: int = Field(..., gt=0)
    origin_location_id: int | None = Field(None, gt=0)
    destination_location_id: int | None = Field(None, gt=0)


class TransferReceiveUpdate(BaseModel):
    """Payload an Operator may send to PUT /transfers/{id}.

    The Operator role receives units, so it may confirm the arrival. Every
    other field of a transfer (who dispatched it, when, from where to where)
    belongs to the dispatch record and must not be rewritten by the role
    that receives: ``extra="forbid"`` rejects any attempt with 422.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal[TransferStatus.RECEIVED]


class UnitTransferRequest(BaseModel):
    """Body for the unit-detail-page "Transferir"/"Vender" action.

    `to_location_id` present -> dispatch the unit to that location (IN_TRANSIT).
    `to_location_id` absent -> sell the unit (SOLD), per
    TransferService.transfer_unit_with_status_update.
    """

    from_location_id: int | None = Field(None, gt=0)
    to_location_id: int | None = Field(None, gt=0)
    notes: str | None = None


class TransferUpdate(BaseModel):
    """Transfer update payload (PUT /transfers/{id}).

    ``extra="forbid"``: only the fields declared here are accepted.
    """

    model_config = ConfigDict(extra="forbid")

    unit_id: int | None = Field(None, gt=0)
    dispatched_by_id: int | None = Field(None, gt=0)
    received_by_id: int | None = Field(None, gt=0)
    origin_location_id: int | None = Field(None, gt=0)
    destination_location_id: int | None = Field(None, gt=0)
    status: TransferStatus | None = None
    dispatched_at: datetime | None = None
    received_at: datetime | None = None


class TransferFilters(BaseModel):
    unit_id: int | None = None
    status: TransferStatus | None = None
    origin_location_id: int | None = None
    destination_location_id: int | None = None
    dispatched_by_id: int | None = None
    received_by_id: int | None = None


class Transfer(TransferBase):
    id: int
    dispatched_by_name: str | None = None
    model_config = ConfigDict(from_attributes=True)


class TransferStats(BaseModel):
    total_transfers: int
    pending_transfers: int
    in_transit_transfers: int
    received_transfers: int
    cancelled: int
    recent_transfers: list[Transfer]
