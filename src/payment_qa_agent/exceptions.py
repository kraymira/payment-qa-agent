"""Domain errors raised by the payment core."""

from payment_qa_agent.models import PaymentStatus


class PaymentError(Exception):
    """Base class for expected payment-domain errors."""


class PaymentNotFound(PaymentError):
    """Raised when a payment ID is unknown to the service."""

    def __init__(self, payment_id: str) -> None:
        super().__init__(f"payment not found: {payment_id}")


class IdempotencyConflict(PaymentError):
    """Raised when one idempotency key is reused for a different request."""

    def __init__(self, idempotency_key: str) -> None:
        super().__init__(
            "idempotency key was already used for a different request: "
            f"{idempotency_key}"
        )


class InvalidPaymentTransition(PaymentError):
    """Raised when the payment state machine rejects a transition."""

    def __init__(
        self,
        current_status: PaymentStatus,
        new_status: PaymentStatus,
    ) -> None:
        super().__init__(
            f"payment cannot transition from {current_status} to {new_status}"
        )
