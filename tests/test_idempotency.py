from decimal import Decimal

import pytest

from payment_qa_agent import IdempotencyConflict, PaymentService, PaymentStatus


def test_repeated_request_returns_original_payment() -> None:
    service = PaymentService()

    first_payment = service.create_payment(
        idempotency_key="checkout-123",
        amount=Decimal("19.99"),
        currency="eur",
    )
    repeated_payment = service.create_payment(
        idempotency_key="checkout-123",
        amount=Decimal("19.99"),
        currency="EUR",
    )

    assert repeated_payment == first_payment
    assert repeated_payment.status is PaymentStatus.CREATED


def test_same_key_cannot_be_reused_for_different_amount() -> None:
    service = PaymentService()
    service.create_payment(
        idempotency_key="checkout-123",
        amount=Decimal("19.99"),
        currency="EUR",
    )

    with pytest.raises(IdempotencyConflict):
        service.create_payment(
            idempotency_key="checkout-123",
            amount=Decimal("29.99"),
            currency="EUR",
        )


def test_different_keys_create_different_payments() -> None:
    service = PaymentService()

    first_payment = service.create_payment(
        idempotency_key="checkout-123",
        amount=Decimal("19.99"),
        currency="EUR",
    )
    second_payment = service.create_payment(
        idempotency_key="checkout-456",
        amount=Decimal("19.99"),
        currency="EUR",
    )

    assert second_payment.payment_id != first_payment.payment_id


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-0.01")])
def test_non_positive_amount_is_rejected(amount: Decimal) -> None:
    service = PaymentService()

    with pytest.raises(ValueError, match="amount must be greater than zero"):
        service.create_payment(
            idempotency_key="checkout-123",
            amount=amount,
            currency="EUR",
        )
