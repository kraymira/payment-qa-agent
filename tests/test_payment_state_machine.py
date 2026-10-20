from decimal import Decimal

import pytest

from payment_qa_agent import (
    InvalidPaymentTransition,
    Payment,
    PaymentNotFound,
    PaymentService,
    PaymentStatus,
)
from payment_qa_agent.models import can_transition


def create_payment(service: PaymentService) -> Payment:
    return service.create_payment(
        idempotency_key="checkout-123",
        amount=Decimal("19.99"),
        currency="EUR",
    )


@pytest.mark.parametrize(
    "final_status",
    [PaymentStatus.COMPLETED, PaymentStatus.FAILED],
)
# Risk: the service rejects a valid payment-processing path.
def test_pending_payment_can_reach_supported_final_status(
    final_status: PaymentStatus,
) -> None:
    service = PaymentService()
    payment = create_payment(service)

    pending_payment = service.transition_payment(
        payment.payment_id,
        PaymentStatus.PENDING,
    )
    final_payment = service.transition_payment(
        payment.payment_id,
        final_status,
    )

    assert pending_payment.status is PaymentStatus.PENDING
    assert final_payment.status is final_status
    assert service.get_payment(payment.payment_id) == final_payment


# Risk: an early provider or validation failure cannot be represented.
def test_created_payment_can_fail_immediately() -> None:
    service = PaymentService()
    payment = create_payment(service)

    failed_payment = service.transition_payment(
        payment.payment_id,
        PaymentStatus.FAILED,
    )

    assert failed_payment.status is PaymentStatus.FAILED


def assert_transition_is_rejected_without_changing_payment(
    service: PaymentService,
    payment: Payment,
    current_status: PaymentStatus,
    new_status: PaymentStatus,
) -> None:
    timeline_before = service.get_timeline(payment.payment_id)

    with pytest.raises(InvalidPaymentTransition):
        service.transition_payment(payment.payment_id, new_status)

    assert service.get_payment(payment.payment_id).status is current_status
    assert service.get_timeline(payment.payment_id) == timeline_before


# Risk: a payment skips the required processing step.
def test_created_payment_cannot_skip_pending() -> None:
    service = PaymentService()
    payment = create_payment(service)

    assert_transition_is_rejected_without_changing_payment(
        service,
        payment,
        PaymentStatus.CREATED,
        PaymentStatus.COMPLETED,
    )


# Risk: a completed payment changes after reaching a final state.
def test_completed_payment_cannot_change_again() -> None:
    service = PaymentService()
    payment = create_payment(service)
    service.transition_payment(payment.payment_id, PaymentStatus.PENDING)
    completed_payment = service.transition_payment(
        payment.payment_id,
        PaymentStatus.COMPLETED,
    )

    assert_transition_is_rejected_without_changing_payment(
        service,
        completed_payment,
        PaymentStatus.COMPLETED,
        PaymentStatus.FAILED,
    )


# Risk: a failed payment restarts processing without a deliberate retry operation.
def test_failed_payment_cannot_restart() -> None:
    service = PaymentService()
    payment = create_payment(service)
    failed_payment = service.transition_payment(
        payment.payment_id,
        PaymentStatus.FAILED,
    )

    assert_transition_is_rejected_without_changing_payment(
        service,
        failed_payment,
        PaymentStatus.FAILED,
        PaymentStatus.PENDING,
    )


@pytest.mark.parametrize(
    ("current_status", "new_status", "expected"),
    [
        (PaymentStatus.CREATED, PaymentStatus.CREATED, False),
        (PaymentStatus.CREATED, PaymentStatus.PENDING, True),
        (PaymentStatus.CREATED, PaymentStatus.COMPLETED, False),
        (PaymentStatus.CREATED, PaymentStatus.FAILED, True),
        (PaymentStatus.PENDING, PaymentStatus.CREATED, False),
        (PaymentStatus.PENDING, PaymentStatus.PENDING, False),
        (PaymentStatus.PENDING, PaymentStatus.COMPLETED, True),
        (PaymentStatus.PENDING, PaymentStatus.FAILED, True),
        (PaymentStatus.COMPLETED, PaymentStatus.CREATED, False),
        (PaymentStatus.COMPLETED, PaymentStatus.PENDING, False),
        (PaymentStatus.COMPLETED, PaymentStatus.COMPLETED, False),
        (PaymentStatus.COMPLETED, PaymentStatus.FAILED, False),
        (PaymentStatus.FAILED, PaymentStatus.CREATED, False),
        (PaymentStatus.FAILED, PaymentStatus.PENDING, False),
        (PaymentStatus.FAILED, PaymentStatus.COMPLETED, False),
        (PaymentStatus.FAILED, PaymentStatus.FAILED, False),
    ],
)
# Risk: an untested cell in the transition table changes the payment lifecycle.
def test_complete_transition_table(
    current_status: PaymentStatus,
    new_status: PaymentStatus,
    expected: bool,
) -> None:
    assert can_transition(current_status, new_status) is expected


# Risk: an unknown payment ID is silently treated as a real payment.
def test_get_unknown_payment_is_rejected() -> None:
    service = PaymentService()

    with pytest.raises(PaymentNotFound, match="missing-payment"):
        service.get_payment("missing-payment")


# Risk: a state transition silently creates or modifies an unknown payment.
def test_transition_unknown_payment_is_rejected() -> None:
    service = PaymentService()

    with pytest.raises(PaymentNotFound, match="missing-payment"):
        service.transition_payment("missing-payment", PaymentStatus.PENDING)
