"""Validated input and output contracts for deterministic triage."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from payment_qa_agent.models import PaymentStatus


NonEmptyString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class Classification(StrEnum):
    """Categories that may be returned by the triage workflow."""

    PRODUCT_BUG = "product_bug"
    TEST_BUG = "test_bug"
    INFRASTRUCTURE_ISSUE = "infrastructure_issue"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class Invariant(StrEnum):
    """Financial rules understood by the deterministic classifier."""

    IDEMPOTENCY = "one idempotency key must map to one payment"
    COMPLETED_IS_TERMINAL = "completed payment must remain completed"


class TimelineEntry(BaseModel):
    """One payment event supplied as evidence in a failure bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: NonEmptyString
    payment_id: NonEmptyString
    previous_status: PaymentStatus | None
    current_status: PaymentStatus
    occurred_at: datetime

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, occurred_at: datetime) -> datetime:
        """Reject timestamps whose ordering depends on a local timezone."""

        if occurred_at.tzinfo is None or occurred_at.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return occurred_at


class FailureBundle(BaseModel):
    """Validated facts available to the deterministic classifier."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    test_name: NonEmptyString
    assertion: NonEmptyString
    payment_ids: list[NonEmptyString]
    timeline: list[TimelineEntry]
    invariant: Invariant | None

    @field_validator("payment_ids")
    @classmethod
    def require_unique_payment_ids(cls, payment_ids: list[str]) -> list[str]:
        """Reject duplicated identifiers that do not add new evidence."""

        if len(payment_ids) != len(set(payment_ids)):
            raise ValueError("payment_ids must be unique")
        return payment_ids

    @model_validator(mode="after")
    def validate_timeline(self) -> Self:
        """Require an ordered timeline that references listed payments."""

        event_ids = [event.event_id for event in self.timeline]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("timeline event IDs must be unique")

        known_payment_ids = set(self.payment_ids)
        unknown_payment_ids = {
            event.payment_id
            for event in self.timeline
            if event.payment_id not in known_payment_ids
        }
        if unknown_payment_ids:
            unknown = ", ".join(sorted(unknown_payment_ids))
            raise ValueError(
                f"timeline references unknown payment IDs: {unknown}"
            )

        timestamps = [event.occurred_at for event in self.timeline]
        if timestamps != sorted(timestamps):
            raise ValueError("timeline events must be ordered by occurred_at")

        return self

    @property
    def evidence_ids(self) -> frozenset[str]:
        """Return every evidence identifier that a result may cite."""

        evidence_ids = {"assertion"}
        if self.invariant is not None:
            evidence_ids.add("invariant")
        evidence_ids.update(
            f"payment:{payment_id}" for payment_id in self.payment_ids
        )
        evidence_ids.update(
            f"event:{event.event_id}" for event in self.timeline
        )
        return frozenset(evidence_ids)


class TriageResult(BaseModel):
    """Structured deterministic classification with cited evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    classification: Classification
    probable_cause: NonEmptyString
    evidence_ids: list[NonEmptyString] = Field(min_length=1)
    requires_human_review: bool

    @field_validator("evidence_ids")
    @classmethod
    def require_unique_evidence_ids(
        cls,
        evidence_ids: list[str],
    ) -> list[str]:
        """Keep each cited fact identifiable exactly once."""

        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence_ids must be unique")
        return evidence_ids
