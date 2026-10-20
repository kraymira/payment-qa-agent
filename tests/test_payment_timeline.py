from datetime import UTC
from decimal import Decimal

import pytest

from payment_qa_agent import PaymentNotFound, PaymentService, PaymentStatus


# Risk: missing or unordered evidence makes payment investigation unreliable.
def test_timeline_contains_creation_and_state_changes_in_order() -> None:
    service = PaymentService()
    payment = service.create_payment(
        idempotency_key="checkout-123",
        amount=Decimal("19.99"),
        currency="EUR",
    )
    service.transition_payment(payment.payment_id, PaymentStatus.PENDING)
    service.transition_payment(payment.payment_id, PaymentStatus.COMPLETED)

    timeline = service.get_timeline(payment.payment_id)

    assert [event.current_status for event in timeline] == [
        PaymentStatus.CREATED,
        PaymentStatus.PENDING,
        PaymentStatus.COMPLETED,
    ]
    assert [event.previous_status for event in timeline] == [
        None,
        PaymentStatus.CREATED,
        PaymentStatus.PENDING,
    ]
    assert all(event.payment_id == payment.payment_id for event in timeline)
    assert all(event.occurred_at.tzinfo is UTC for event in timeline)


# Risk: an unknown payment is presented as a real payment with an empty history.
def test_timeline_for_unknown_payment_is_rejected() -> None:
    service = PaymentService()

    with pytest.raises(PaymentNotFound, match="missing-payment"):
        service.get_timeline("missing-payment")
