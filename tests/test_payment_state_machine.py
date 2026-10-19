from decimal import Decimal

import pytest

from payment_qa_agent import (
    InvalidPaymentTransition,
    Payment,
    PaymentNotFound,
    PaymentService,
    PaymentStatus,
)


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


def test_created_payment_can_fail_immediately() -> None:
    service = PaymentService()
    payment = create_payment(service)

    failed_payment = service.transition_payment(
        payment.payment_id,
        PaymentStatus.FAILED,
    )

    assert failed_payment.status is PaymentStatus.FAILED


@pytest.mark.parametrize(
    ("current_status", "new_status"),
    [
        (PaymentStatus.CREATED, PaymentStatus.COMPLETED),
        (PaymentStatus.COMPLETED, PaymentStatus.FAILED),
        (PaymentStatus.FAILED, PaymentStatus.PENDING),
    ],
)
def test_invalid_transition_is_rejected_without_changing_payment(
    current_status: PaymentStatus,
    new_status: PaymentStatus,
) -> None:
    service = PaymentService()
    payment = create_payment(service)

    if current_status is PaymentStatus.COMPLETED:
        service.transition_payment(payment.payment_id, PaymentStatus.PENDING)
        service.transition_payment(payment.payment_id, PaymentStatus.COMPLETED)
    elif current_status is PaymentStatus.FAILED:
        service.transition_payment(payment.payment_id, PaymentStatus.FAILED)

    timeline_before = service.get_timeline(payment.payment_id)

    with pytest.raises(InvalidPaymentTransition):
        service.transition_payment(payment.payment_id, new_status)

    assert service.get_payment(payment.payment_id).status is current_status
    assert service.get_timeline(payment.payment_id) == timeline_before


def test_unknown_payment_is_rejected() -> None:
    service = PaymentService()

    with pytest.raises(PaymentNotFound, match="missing-payment"):
        service.get_payment("missing-payment")
