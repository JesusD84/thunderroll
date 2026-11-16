from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models.models import TransferStatus


class TransferBase(BaseModel):
    """A transfer, as the API returns it.

    This is the *record* of a movement: who dispatched it, who received it
    and when. Those fields are written by the server, never by a client.
    """

    unit_id: int
    dispatched_by_id: int | None = None
    received_by_id: int | None = None
    origin_location_id: int | None = None
    destination_location_id: int | None = None
    status: TransferStatus
    dispatched_at: datetime | None = None
    received_at: datetime | None = None


class TransferCreate(BaseModel):
    """Dispatch payload (POST /transfers/).

    The attribution of a dispatch belongs to the server: who sent the unit
    and when are taken from the session and from the server clock, so they
    are not part of this schema and ``extra="forbid"`` rejects them with 422.

    The status is the server's too: a dispatch always starts as PENDING, and
    the state of the unit follows the transfer.
    """

    model_config = ConfigDict(extra="forbid")

    unit_id: int = Field(..., gt=0)
    origin_location_id: int | None = Field(None, gt=0)
    destination_location_id: int = Field(..., gt=0)


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

    `to_location_id` present -> dispatch the unit to that location.
    `to_location_id` absent -> sell the unit, through the sale service, so
    there is only one way to sell a unit.
    """

    from_location_id: int | None = Field(None, gt=0)
    to_location_id: int | None = Field(None, gt=0)
    notes: str | None = None


class TransferUpdate(BaseModel):
    """Transfer update payload (PUT /transfers/{id}).

    Only the status may change: a transfer is closed as RECEIVED (the unit
    arrived) or CANCELLED (it never left). Rewriting who dispatched it,
    when, or the route would falsify the trail, so those fields are not
    part of this schema and ``extra="forbid"`` rejects them with 422.
    """

    model_config = ConfigDict(extra="forbid")

    status: TransferStatus


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
