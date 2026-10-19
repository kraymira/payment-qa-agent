"""In-memory payment service used by the test harness."""

from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from payment_qa_agent.models import Payment


class IdempotencyConflict(ValueError):
    """Raised when an idempotency key is reused for a different request."""


@dataclass(frozen=True, slots=True)
class _StoredRequest:
    amount: Decimal
    currency: str
    payment: Payment


class PaymentService:
    """Creates payments while enforcing idempotent request semantics."""

    def __init__(self) -> None:
        self._requests_by_key: dict[str, _StoredRequest] = {}

    def create_payment(
        self,
        *,
        idempotency_key: str,
        amount: Decimal,
        currency: str,
    ) -> Payment:
        if not idempotency_key.strip():
            raise ValueError("idempotency_key must not be empty")
        if amount <= Decimal("0"):
            raise ValueError("amount must be greater than zero")

        normalized_currency = currency.strip().upper()
        if len(normalized_currency) != 3 or not normalized_currency.isalpha():
            raise ValueError("currency must be a three-letter code")

        stored = self._requests_by_key.get(idempotency_key)
        if stored is not None:
            if stored.amount != amount or stored.currency != normalized_currency:
                raise IdempotencyConflict(
                    "idempotency key was already used for a different request"
                )
            return stored.payment

        payment = Payment(
            payment_id=str(uuid4()),
            amount=amount,
            currency=normalized_currency,
        )
        self._requests_by_key[idempotency_key] = _StoredRequest(
            amount=amount,
            currency=normalized_currency,
            payment=payment,
        )
        return payment
