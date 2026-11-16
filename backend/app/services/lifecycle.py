"""The lifecycle of a unit and of a transfer, defined in one place.

This module is the single source of truth for *which* state changes are
allowed. The services ask it before they write anything, so a unit can never
end up in a state the traceability rules do not allow, and the rules are
written down once instead of being spread over the services.

Units
    ``WAREHOUSE_UNIDENTIFIED`` -> ``AVAILABLE`` | ``IN_TRANSIT`` | ``SOLD``
    ``AVAILABLE``              -> ``IN_TRANSIT`` | ``SOLD``
    ``IN_TRANSIT``             -> ``AVAILABLE``
    ``SOLD``                   -> (nothing: the sale is final)

    A unit that reaches the warehouse without a serial number can still be
    dispatched or sold: there is no dead end. A unit that is on the road
    (``IN_TRANSIT``) has to be received before it can be sold.

Transfers
    ``PENDING``    -> ``RECEIVED`` | ``CANCELLED``
    ``IN_TRANSIT`` -> ``RECEIVED`` | ``CANCELLED``
    ``RECEIVED``   -> (nothing: the trip is closed)
    ``CANCELLED``  -> (nothing: the trip never happened)

    ``PENDING`` and ``IN_TRANSIT`` are the *active* statuses: a unit has at
    most one active transfer at a time.

The unit state is not chosen freely: it is derived from the state of the
transfer that explains it (see ``UNIT_STATUS_BY_TRANSFER_STATUS``).
"""

from __future__ import annotations

from app.models.models import TransferStatus, UnitStatus

#: Which unit status may follow which one.
UNIT_STATUS_TRANSITIONS: dict[UnitStatus, frozenset[UnitStatus]] = {
    UnitStatus.WAREHOUSE_UNIDENTIFIED: frozenset(
        {UnitStatus.AVAILABLE, UnitStatus.IN_TRANSIT, UnitStatus.SOLD}
    ),
    UnitStatus.AVAILABLE: frozenset({UnitStatus.IN_TRANSIT, UnitStatus.SOLD}),
    UnitStatus.IN_TRANSIT: frozenset({UnitStatus.AVAILABLE}),
    UnitStatus.SOLD: frozenset(),
}

#: Which transfer status may follow which one.
TRANSFER_STATUS_TRANSITIONS: dict[TransferStatus, frozenset[TransferStatus]] = {
    TransferStatus.PENDING: frozenset(
        {TransferStatus.RECEIVED, TransferStatus.CANCELLED}
    ),
    TransferStatus.IN_TRANSIT: frozenset(
        {TransferStatus.RECEIVED, TransferStatus.CANCELLED}
    ),
    TransferStatus.RECEIVED: frozenset(),
    TransferStatus.CANCELLED: frozenset(),
}

#: The statuses of a transfer that still hold the unit.
ACTIVE_TRANSFER_STATUSES: tuple[TransferStatus, ...] = (
    TransferStatus.PENDING,
    TransferStatus.IN_TRANSIT,
)

#: The unit state that comes out of a transfer in each status.
#:
#: A dispatch (PENDING) puts the unit on the road; closing the transfer
#: either receives it at the destination or brings it back to the origin.
UNIT_STATUS_BY_TRANSFER_STATUS: dict[TransferStatus, UnitStatus] = {
    TransferStatus.PENDING: UnitStatus.IN_TRANSIT,
    TransferStatus.IN_TRANSIT: UnitStatus.IN_TRANSIT,
    TransferStatus.RECEIVED: UnitStatus.AVAILABLE,
    TransferStatus.CANCELLED: UnitStatus.AVAILABLE,
}


class InvalidTransition(Exception):
    """A state change the lifecycle does not allow."""

    def __init__(
        self,
        entity: str,
        current: object,
        target: object,
        allowed: frozenset,
    ) -> None:
        self.entity = entity
        self.current = current
        self.target = target
        self.allowed = allowed
        super().__init__(self._message())

    def _message(self) -> str:
        allowed = ", ".join(sorted(str(status) for status in self.allowed)) or "none"
        return (
            f"Invalid {self.entity} transition: {self.current} -> {self.target}. "
            f"Allowed from {self.current}: {allowed}."
        )


def can_transition_unit(current: UnitStatus, target: UnitStatus) -> bool:
    """True when a unit may go from ``current`` to ``target``."""
    return target in UNIT_STATUS_TRANSITIONS.get(current, frozenset())


def can_transition_transfer(current: TransferStatus, target: TransferStatus) -> bool:
    """True when a transfer may go from ``current`` to ``target``."""
    return target in TRANSFER_STATUS_TRANSITIONS.get(current, frozenset())


def ensure_unit_transition(current: UnitStatus, target: UnitStatus) -> None:
    """Raise ``InvalidTransition`` when a unit may not change like that."""
    if not can_transition_unit(current, target):
        raise InvalidTransition(
            "unit status",
            current,
            target,
            UNIT_STATUS_TRANSITIONS.get(current, frozenset()),
        )


def ensure_transfer_transition(current: TransferStatus, target: TransferStatus) -> None:
    """Raise ``InvalidTransition`` when a transfer may not change like that."""
    if not can_transition_transfer(current, target):
        raise InvalidTransition(
            "transfer status",
            current,
            target,
            TRANSFER_STATUS_TRANSITIONS.get(current, frozenset()),
        )


def unit_status_for_transfer(status: TransferStatus) -> UnitStatus:
    """The unit state that comes out of a transfer in ``status``."""
    return UNIT_STATUS_BY_TRANSFER_STATUS[status]


def is_active_transfer(status: TransferStatus) -> bool:
    """True while a transfer still holds the unit."""
    return status in ACTIVE_TRANSFER_STATUSES
