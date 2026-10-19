"""Validation functions used at the payment-core boundary."""

from decimal import Decimal


def validate_amount(amount: Decimal) -> Decimal:
    """Require a finite positive Decimal amount."""

    if not isinstance(amount, Decimal):
        raise TypeError("amount must be a Decimal")
    if not amount.is_finite():
        raise ValueError("amount must be finite")
    if amount <= Decimal(0):
        raise ValueError("amount must be greater than zero")
    return amount


def normalize_currency(currency: str) -> str:
    """Normalize and validate a three-letter ASCII currency code."""

    if not isinstance(currency, str):
        raise TypeError("currency must be a string")

    normalized_currency = currency.strip().upper()
    if (
        len(normalized_currency) != 3
        or not normalized_currency.isascii()
        or not normalized_currency.isalpha()
    ):
        raise ValueError("currency must be a three-letter code")
    return normalized_currency


def normalize_idempotency_key(idempotency_key: str) -> str:
    """Trim and require a non-empty idempotency key."""

    if not isinstance(idempotency_key, str):
        raise TypeError("idempotency_key must be a string")

    normalized_key = idempotency_key.strip()
    if not normalized_key:
        raise ValueError("idempotency_key must not be empty")
    return normalized_key
