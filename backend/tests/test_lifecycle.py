"""The lifecycle rules themselves.

``app/services/lifecycle.py`` is the single source of truth for the allowed
transitions. These tests pin the tables down, so a change in the rules is
always a deliberate one.
"""

import pytest

from app.models.models import TransferStatus, UnitStatus
from app.services import lifecycle

# ---------------------------------------------------------------------------
# The unit transitions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (UnitStatus.WAREHOUSE_UNIDENTIFIED, UnitStatus.AVAILABLE),
        (UnitStatus.WAREHOUSE_UNIDENTIFIED, UnitStatus.IN_TRANSIT),
        (UnitStatus.WAREHOUSE_UNIDENTIFIED, UnitStatus.SOLD),
        (UnitStatus.AVAILABLE, UnitStatus.IN_TRANSIT),
        (UnitStatus.AVAILABLE, UnitStatus.SOLD),
        (UnitStatus.IN_TRANSIT, UnitStatus.AVAILABLE),
    ],
)
def test_allowed_unit_transitions(current, target):
    """The transitions the system allows."""
    assert lifecycle.can_transition_unit(current, target)
    lifecycle.ensure_unit_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (UnitStatus.AVAILABLE, UnitStatus.AVAILABLE),
        (UnitStatus.AVAILABLE, UnitStatus.WAREHOUSE_UNIDENTIFIED),
        (UnitStatus.IN_TRANSIT, UnitStatus.SOLD),
        (UnitStatus.IN_TRANSIT, UnitStatus.IN_TRANSIT),
        (UnitStatus.IN_TRANSIT, UnitStatus.WAREHOUSE_UNIDENTIFIED),
        (UnitStatus.SOLD, UnitStatus.AVAILABLE),
        (UnitStatus.SOLD, UnitStatus.IN_TRANSIT),
        (UnitStatus.SOLD, UnitStatus.WAREHOUSE_UNIDENTIFIED),
    ],
)
def test_forbidden_unit_transitions(current, target):
    """The transitions the system refuses."""
    assert not lifecycle.can_transition_unit(current, target)
    with pytest.raises(lifecycle.InvalidTransition):
        lifecycle.ensure_unit_transition(current, target)


def test_a_sold_unit_is_final():
    """The sale is final: there is no way back from SOLD."""
    assert lifecycle.UNIT_STATUS_TRANSITIONS[UnitStatus.SOLD] == frozenset()


def test_no_unit_stays_where_it_is():
    """A transition always changes the state."""
    for current, targets in lifecycle.UNIT_STATUS_TRANSITIONS.items():
        assert current not in targets


# ---------------------------------------------------------------------------
# The transfer transitions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (TransferStatus.PENDING, TransferStatus.RECEIVED),
        (TransferStatus.PENDING, TransferStatus.CANCELLED),
        (TransferStatus.IN_TRANSIT, TransferStatus.RECEIVED),
        (TransferStatus.IN_TRANSIT, TransferStatus.CANCELLED),
    ],
)
def test_allowed_transfer_transitions(current, target):
    """The transitions the system allows."""
    assert lifecycle.can_transition_transfer(current, target)
    lifecycle.ensure_transfer_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (TransferStatus.PENDING, TransferStatus.IN_TRANSIT),
        (TransferStatus.RECEIVED, TransferStatus.RECEIVED),
        (TransferStatus.RECEIVED, TransferStatus.CANCELLED),
        (TransferStatus.CANCELLED, TransferStatus.RECEIVED),
        (TransferStatus.CANCELLED, TransferStatus.IN_TRANSIT),
    ],
)
def test_forbidden_transfer_transitions(current, target):
    """The transitions the system refuses."""
    assert not lifecycle.can_transition_transfer(current, target)
    with pytest.raises(lifecycle.InvalidTransition):
        lifecycle.ensure_transfer_transition(current, target)


def test_the_active_statuses_are_the_ones_that_hold_the_unit():
    """A unit is held by a pending or in-transit transfer, and by nothing else."""
    assert set(lifecycle.ACTIVE_TRANSFER_STATUSES) == {
        TransferStatus.PENDING,
        TransferStatus.IN_TRANSIT,
    }
    assert lifecycle.is_active_transfer(TransferStatus.PENDING)
    assert lifecycle.is_active_transfer(TransferStatus.IN_TRANSIT)
    assert not lifecycle.is_active_transfer(TransferStatus.RECEIVED)
    assert not lifecycle.is_active_transfer(TransferStatus.CANCELLED)


# ---------------------------------------------------------------------------
# The unit state comes out of the transfer
# ---------------------------------------------------------------------------


def test_the_unit_state_follows_the_transfer():
    """A dispatch puts the unit on the road; closing the trip settles it."""
    assert (
        lifecycle.unit_status_for_transfer(TransferStatus.PENDING)
        == UnitStatus.IN_TRANSIT
    )
    assert (
        lifecycle.unit_status_for_transfer(TransferStatus.IN_TRANSIT)
        == UnitStatus.IN_TRANSIT
    )
    assert (
        lifecycle.unit_status_for_transfer(TransferStatus.RECEIVED)
        == UnitStatus.AVAILABLE
    )
    assert (
        lifecycle.unit_status_for_transfer(TransferStatus.CANCELLED)
        == UnitStatus.AVAILABLE
    )


def test_every_transfer_status_maps_to_a_unit_status():
    """There is no transfer status without a unit state."""
    for status in TransferStatus:
        assert status in lifecycle.UNIT_STATUS_BY_TRANSFER_STATUS


def test_the_invalid_transition_says_what_is_allowed():
    """The error explains the rule it enforces."""
    with pytest.raises(lifecycle.InvalidTransition) as exc:
        lifecycle.ensure_unit_transition(UnitStatus.IN_TRANSIT, UnitStatus.SOLD)

    message = str(exc.value)
    assert "IN_TRANSIT" in message
    assert "SOLD" in message
    assert "AVAILABLE" in message
