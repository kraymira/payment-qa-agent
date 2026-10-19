from decimal import Decimal

import pytest

from payment_qa_agent import (
    IdempotencyConflict,
    PaymentService,
    PaymentStatus,
)


def test_create_payment_normalizes_input() -> None:
    service = PaymentService()

    payment = service.create_payment(
        idempotency_key="  checkout-123  ",
        amount=Decimal("19.99"),
        currency=" eur ",
    )

    assert payment.payment_id.startswith("pay_")
    assert payment.amount == Decimal("19.99")
    assert payment.currency == "EUR"
    assert payment.status is PaymentStatus.CREATED


def test_repeated_request_returns_same_payment() -> None:
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
    assert len(service.get_timeline(first_payment.payment_id)) == 1


@pytest.mark.parametrize(
    ("amount", "currency"),
    [
        (Decimal("29.99"), "EUR"),
        (Decimal("19.99"), "USD"),
    ],
)
def test_same_key_rejects_different_payload(
    amount: Decimal,
    currency: str,
) -> None:
    service = PaymentService()
    service.create_payment(
        idempotency_key="checkout-123",
        amount=Decimal("19.99"),
        currency="EUR",
    )

    with pytest.raises(IdempotencyConflict, match="checkout-123"):
        service.create_payment(
            idempotency_key="checkout-123",
            amount=amount,
            currency=currency,
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


@pytest.mark.parametrize("amount", [Decimal(0), Decimal("-0.01")])
def test_non_positive_amount_is_rejected(amount: Decimal) -> None:
    service = PaymentService()

    with pytest.raises(ValueError, match="amount must be greater than zero"):
        service.create_payment(
            idempotency_key="checkout-123",
            amount=amount,
            currency="EUR",
        )


@pytest.mark.parametrize("amount", [Decimal("NaN"), Decimal("Infinity")])
def test_non_finite_amount_is_rejected(amount: Decimal) -> None:
    service = PaymentService()

    with pytest.raises(ValueError, match="amount must be finite"):
        service.create_payment(
            idempotency_key="checkout-123",
            amount=amount,
            currency="EUR",
        )


@pytest.mark.parametrize("currency", ["EU", "EURO", "12A", "евр"])
def test_invalid_currency_is_rejected(currency: str) -> None:
    service = PaymentService()

    with pytest.raises(ValueError, match="three-letter code"):
        service.create_payment(
            idempotency_key="checkout-123",
            amount=Decimal("19.99"),
            currency=currency,
        )


@pytest.mark.parametrize("idempotency_key", ["", "   "])
def test_empty_idempotency_key_is_rejected(idempotency_key: str) -> None:
    service = PaymentService()

    with pytest.raises(ValueError, match="must not be empty"):
        service.create_payment(
            idempotency_key=idempotency_key,
            amount=Decimal("19.99"),
            currency="EUR",
        )
