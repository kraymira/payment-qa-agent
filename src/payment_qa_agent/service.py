"""In-memory operations for the deterministic payment core."""

from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from payment_qa_agent.exceptions import (
    IdempotencyConflict,
    InvalidPaymentTransition,
    PaymentNotFound,
)
from payment_qa_agent.models import (
    Payment,
    PaymentEvent,
    PaymentStatus,
    can_transition,
)
from payment_qa_agent.validation import (
    normalize_currency,
    normalize_idempotency_key,
    validate_amount,
)


@dataclass(frozen=True, slots=True)
class _StoredRequest:
    amount: Decimal
    currency: str
    payment_id: str


class PaymentService:
    """Create payments and move them through an explicit state machine."""

    def __init__(self) -> None:
        self._payments_by_id: dict[str, Payment] = {}
        self._requests_by_key: dict[str, _StoredRequest] = {}
        self._events_by_payment_id: dict[str, list[PaymentEvent]] = {}

    def create_payment(
        self,
        *,
        idempotency_key: str,
        amount: Decimal,
        currency: str,
    ) -> Payment:
        """Create a payment or return the payment created by the same request."""

        normalized_key = normalize_idempotency_key(idempotency_key)
        validated_amount = validate_amount(amount)
        normalized_currency = normalize_currency(currency)

        stored_request = self._requests_by_key.get(normalized_key)
        if stored_request is not None:
            if (
                stored_request.amount != validated_amount
                or stored_request.currency != normalized_currency
            ):
                raise IdempotencyConflict(normalized_key)
            return self._payments_by_id[stored_request.payment_id]

        payment = Payment(
            payment_id=f"pay_{uuid4().hex}",
            amount=validated_amount,
            currency=normalized_currency,
            status=PaymentStatus.CREATED,
        )
        self._payments_by_id[payment.payment_id] = payment
        self._requests_by_key[normalized_key] = _StoredRequest(
            amount=validated_amount,
            currency=normalized_currency,
            payment_id=payment.payment_id,
        )
        self._events_by_payment_id[payment.payment_id] = []
        self._record_event(
            payment_id=payment.payment_id,
            previous_status=None,
            current_status=PaymentStatus.CREATED,
        )
        return payment

    def get_payment(self, payment_id: str) -> Payment:
        """Return a payment or raise a domain-specific error."""

        try:
            return self._payments_by_id[payment_id]
        except KeyError as error:
            raise PaymentNotFound(payment_id) from error

    def transition_payment(
        self,
        payment_id: str,
        new_status: PaymentStatus,
    ) -> Payment:
        """Apply one valid state transition and record it in the timeline."""

        if not isinstance(new_status, PaymentStatus):
            raise TypeError("new_status must be a PaymentStatus")

        payment = self.get_payment(payment_id)
        if not can_transition(payment.status, new_status):
            raise InvalidPaymentTransition(payment.status, new_status)

        updated_payment = replace(payment, status=new_status)
        self._payments_by_id[payment_id] = updated_payment
        self._record_event(
            payment_id=payment_id,
            previous_status=payment.status,
            current_status=new_status,
        )
        return updated_payment

    def get_timeline(self, payment_id: str) -> tuple[PaymentEvent, ...]:
        """Return an immutable view of a payment's ordered events."""

        self.get_payment(payment_id)
        return tuple(self._events_by_payment_id[payment_id])

    def _record_event(
        self,
        *,
        payment_id: str,
        previous_status: PaymentStatus | None,
        current_status: PaymentStatus,
    ) -> None:
        event = PaymentEvent(
            event_id=f"evt_{uuid4().hex}",
            payment_id=payment_id,
            previous_status=previous_status,
            current_status=current_status,
            occurred_at=datetime.now(UTC),
        )
        self._events_by_payment_id[payment_id].append(event)
