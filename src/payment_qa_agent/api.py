"""Minimal HTTP boundary for exercising payment idempotency."""

from decimal import Decimal
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict

from payment_qa_agent.exceptions import IdempotencyConflict, PaymentNotFound
from payment_qa_agent.models import Payment, PaymentStatus
from payment_qa_agent.service import PaymentService


class CreatePaymentRequest(BaseModel):
    """JSON body accepted by ``POST /payments``."""

    model_config = ConfigDict(extra="forbid")

    amount: Decimal
    currency: str


class PaymentResponse(BaseModel):
    """Stable public representation of one payment snapshot."""

    model_config = ConfigDict(extra="forbid")

    payment_id: str
    amount: Decimal
    currency: str
    status: PaymentStatus


def create_app(service: PaymentService | None = None) -> FastAPI:
    """Create an isolated API instance around one payment service."""

    payment_service = service or PaymentService()
    application = FastAPI(
        title="Payment QA Agent API",
        version="0.4.0",
    )

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post(
        "/payments",
        response_model=PaymentResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_payment(
        request: CreatePaymentRequest,
        idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    ) -> PaymentResponse:
        try:
            payment = payment_service.create_payment(
                idempotency_key=idempotency_key,
                amount=request.amount,
                currency=request.currency,
            )
        except IdempotencyConflict as error:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(error),
            ) from error
        except (TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=str(error),
            ) from error
        return _payment_response(payment)

    @application.get(
        "/payments/{payment_id}",
        response_model=PaymentResponse,
    )
    def get_payment(payment_id: str) -> PaymentResponse:
        try:
            payment = payment_service.get_payment(payment_id)
        except PaymentNotFound as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(error),
            ) from error
        return _payment_response(payment)

    return application


def _payment_response(payment: Payment) -> PaymentResponse:
    return PaymentResponse(
        payment_id=payment.payment_id,
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
    )


app = create_app()
