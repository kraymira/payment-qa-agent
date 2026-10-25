"""Pure deterministic rules for payment failure classification."""

from payment_qa_agent.models import PaymentStatus
from payment_qa_agent.triage_models import (
    Classification,
    FailureBundle,
    Invariant,
    TriageResult,
)


def classify(bundle: FailureBundle) -> TriageResult:
    """Classify one failure bundle using only deterministic rules."""

    if (
        bundle.invariant is Invariant.IDEMPOTENCY
        and len(bundle.payment_ids) > 1
    ):
        return _result(
            bundle=bundle,
            classification=Classification.PRODUCT_BUG,
            probable_cause="one idempotency key produced multiple payments",
            evidence_ids=[
                "assertion",
                "invariant",
                *(f"payment:{payment_id}" for payment_id in bundle.payment_ids),
            ],
            requires_human_review=False,
        )

    regressive_events = [
        event
        for event in bundle.timeline
        if event.previous_status is PaymentStatus.COMPLETED
        and event.current_status is PaymentStatus.PENDING
    ]
    if regressive_events:
        event = regressive_events[0]
        evidence_ids = ["assertion", f"event:{event.event_id}"]
        if bundle.invariant is not None:
            evidence_ids.insert(1, "invariant")
        return _result(
            bundle=bundle,
            classification=Classification.PRODUCT_BUG,
            probable_cause="completed payment returned to pending",
            evidence_ids=evidence_ids,
            requires_human_review=False,
        )

    evidence_ids = ["assertion"]
    if bundle.invariant is not None:
        evidence_ids.append("invariant")
    return _result(
        bundle=bundle,
        classification=Classification.INSUFFICIENT_EVIDENCE,
        probable_cause="available evidence does not match a deterministic rule",
        evidence_ids=evidence_ids,
        requires_human_review=True,
    )


def _result(
    *,
    bundle: FailureBundle,
    classification: Classification,
    probable_cause: str,
    evidence_ids: list[str],
    requires_human_review: bool,
) -> TriageResult:
    """Build a result only when every cited evidence ID exists."""

    unknown_evidence_ids = set(evidence_ids) - bundle.evidence_ids
    if unknown_evidence_ids:
        unknown = ", ".join(sorted(unknown_evidence_ids))
        raise ValueError(f"result cites unknown evidence IDs: {unknown}")

    return TriageResult(
        classification=classification,
        probable_cause=probable_cause,
        evidence_ids=evidence_ids,
        requires_human_review=requires_human_review,
    )
