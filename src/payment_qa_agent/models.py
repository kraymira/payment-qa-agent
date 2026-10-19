"""Deterministic payment-domain models."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class PaymentStatus(StrEnum):
    CREATED = "created"
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Payment:
    payment_id: str
    amount: Decimal
    currency: str
    status: PaymentStatus = PaymentStatus.CREATED
