"""Data structures for the deterministic payment domain."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum


class PaymentStatus(StrEnum):
    """Statuses supported by the first version of the payment lifecycle."""

    CREATED = "created"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


_ALLOWED_TRANSITIONS: dict[PaymentStatus, frozenset[PaymentStatus]] = {
    PaymentStatus.CREATED: frozenset({PaymentStatus.PENDING, PaymentStatus.FAILED}),
    PaymentStatus.PENDING: frozenset({PaymentStatus.COMPLETED, PaymentStatus.FAILED}),
    PaymentStatus.COMPLETED: frozenset(),
    PaymentStatus.FAILED: frozenset(),
}


def can_transition(
    current_status: PaymentStatus,
    new_status: PaymentStatus,
) -> bool:
    """Return whether the payment state machine allows a transition."""

    return new_status in _ALLOWED_TRANSITIONS[current_status]


@dataclass(frozen=True, slots=True)
class Payment:
    """An immutable snapshot of a payment at a point in time."""

    payment_id: str
    amount: Decimal
    currency: str
    status: PaymentStatus


@dataclass(frozen=True, slots=True)
class PaymentEvent:
    """One recorded change in a payment lifecycle."""

    event_id: str
    payment_id: str
    previous_status: PaymentStatus | None
    current_status: PaymentStatus
    occurred_at: datetime
