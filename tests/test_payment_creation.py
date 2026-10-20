from decimal import Decimal

import pytest

from payment_qa_agent import (
    IdempotencyConflict,
    PaymentService,
    PaymentStatus,
)


# Risk: equivalent user input is stored inconsistently and bypasses deduplication.
def test_create_payment_normalizes_input() -> None:
    service = PaymentService()

    payment = service.create_payment(
        idempotency_key="  checkout-123  ",
        amount=Decimal("19.99"),
        currency=" eur ",
    )

    assert payment.amount == Decimal("19.99")
    assert payment.currency == "EUR"
    assert payment.status is PaymentStatus.CREATED


# Risk: a client retry after a timeout creates a duplicate payment.
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


# Risk: a retry returns the stale snapshot created before payment processing began.
def test_repeated_request_returns_current_payment_after_status_change() -> None:
    service = PaymentService()
    created_payment = service.create_payment(
        idempotency_key="checkout-123",
        amount=Decimal("19.99"),
        currency="EUR",
    )
    pending_payment = service.transition_payment(
        created_payment.payment_id,
        PaymentStatus.PENDING,
    )

    repeated_payment = service.create_payment(
        idempotency_key="checkout-123",
        amount=Decimal("19.99"),
        currency="EUR",
    )

    assert repeated_payment == pending_payment
    assert repeated_payment.payment_id == created_payment.payment_id
    assert repeated_payment.status is PaymentStatus.PENDING
    assert len(service.get_timeline(created_payment.payment_id)) == 2


@pytest.mark.parametrize(
    ("amount", "currency"),
    [
        (Decimal("29.99"), "EUR"),
        (Decimal("19.99"), "USD"),
    ],
)
# Risk: one idempotency key becomes associated with two different requests.
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


# Risk: deduplication merges two legitimate payment requests.
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
# Risk: an invalid monetary amount enters payment processing.
def test_non_positive_amount_is_rejected(amount: Decimal) -> None:
    service = PaymentService()

    with pytest.raises(ValueError, match="amount must be greater than zero"):
        service.create_payment(
            idempotency_key="checkout-123",
            amount=amount,
            currency="EUR",
        )


@pytest.mark.parametrize("amount", [Decimal("NaN"), Decimal("Infinity")])
# Risk: a non-finite amount breaks comparisons and financial calculations.
def test_non_finite_amount_is_rejected(amount: Decimal) -> None:
    service = PaymentService()

    with pytest.raises(ValueError, match="amount must be finite"):
        service.create_payment(
            idempotency_key="checkout-123",
            amount=amount,
            currency="EUR",
        )


@pytest.mark.parametrize("currency", ["EU", "EURO", "12A", "евр"])
# Risk: malformed currency data reaches downstream payment integrations.
def test_invalid_currency_is_rejected(currency: str) -> None:
    service = PaymentService()

    with pytest.raises(ValueError, match="three-letter code"):
        service.create_payment(
            idempotency_key="checkout-123",
            amount=Decimal("19.99"),
            currency=currency,
        )


@pytest.mark.parametrize("idempotency_key", ["", "   "])
# Risk: retry safety cannot be enforced without a usable request key.
def test_empty_idempotency_key_is_rejected(idempotency_key: str) -> None:
    service = PaymentService()

    with pytest.raises(ValueError, match="must not be empty"):
        service.create_payment(
            idempotency_key=idempotency_key,
            amount=Decimal("19.99"),
            currency="EUR",
        )
