"""Narrow read-only evidence tools available to the triage agent."""

from typing import Protocol

from payment_qa_agent.agent_models import (
    EvidenceItem,
    FailureContextQuery,
    PaymentTimelineQuery,
    TestDefinitionQuery,
    ToolEvidence,
    ToolName,
)
from payment_qa_agent.triage_models import FailureBundle

TEST_DEFINITIONS = {
    "test_retry_does_not_duplicate_payment": (
        "Verify that retrying one logical request is safe.",
        "One idempotency key must always resolve to one payment.",
    ),
    "test_completed_payment_is_terminal": (
        "Verify that completed payments cannot return to an active state.",
        "A completed payment must remain completed.",
    ),
    "test_provider_response": (
        "Verify that the payment provider responds within the test timeout.",
        "The provider call should return before the configured timeout.",
    ),
}


class AgentToolbox(Protocol):
    """Structural allowlist used by the graph and fake toolboxes in tests."""

    def get_failure_context(
        self,
        query: FailureContextQuery,
        bundle: FailureBundle,
    ) -> ToolEvidence: ...

    def get_payment_timeline(
        self,
        query: PaymentTimelineQuery,
        bundle: FailureBundle,
    ) -> ToolEvidence: ...

    def get_test_definition(
        self,
        query: TestDefinitionQuery,
    ) -> ToolEvidence: ...


class ReadOnlyToolbox:
    """Local evidence source with no write or arbitrary file-system access."""

    def get_failure_context(
        self,
        query: FailureContextQuery,
        bundle: FailureBundle,
    ) -> ToolEvidence:
        if query.test_name != bundle.test_name:
            raise ValueError("test_name does not match the failure bundle")

        items = [
            EvidenceItem(
                evidence_id="assertion",
                source=ToolName.FAILURE_CONTEXT,
                content=bundle.assertion,
            )
        ]
        if bundle.invariant is not None:
            items.append(
                EvidenceItem(
                    evidence_id="invariant",
                    source=ToolName.FAILURE_CONTEXT,
                    content=bundle.invariant.value,
                )
            )
        return ToolEvidence(tool=ToolName.FAILURE_CONTEXT, items=tuple(items))

    def get_payment_timeline(
        self,
        query: PaymentTimelineQuery,
        bundle: FailureBundle,
    ) -> ToolEvidence:
        requested = set(query.payment_ids)
        unknown = requested - set(bundle.payment_ids)
        if unknown:
            joined = ", ".join(sorted(unknown))
            raise ValueError(f"timeline requested unknown payment IDs: {joined}")

        items = [
            EvidenceItem(
                evidence_id=f"payment:{payment_id}",
                source=ToolName.PAYMENT_TIMELINE,
                content=f"related payment ID: {payment_id}",
            )
            for payment_id in query.payment_ids
        ]
        items.extend(
            EvidenceItem(
                evidence_id=f"event:{event.event_id}",
                source=ToolName.PAYMENT_TIMELINE,
                content=(
                    f"payment {event.payment_id}: "
                    f"{event.previous_status or 'none'} -> "
                    f"{event.current_status} at {event.occurred_at.isoformat()}"
                ),
            )
            for event in bundle.timeline
            if event.payment_id in requested
        )
        return ToolEvidence(tool=ToolName.PAYMENT_TIMELINE, items=tuple(items))

    def get_test_definition(
        self,
        query: TestDefinitionQuery,
    ) -> ToolEvidence:
        definition = TEST_DEFINITIONS.get(query.test_name)
        if definition is None:
            return ToolEvidence(tool=ToolName.TEST_DEFINITION)

        purpose, expected_behavior = definition
        return ToolEvidence(
            tool=ToolName.TEST_DEFINITION,
            items=(
                EvidenceItem(
                    evidence_id=f"test_definition:{query.test_name}",
                    source=ToolName.TEST_DEFINITION,
                    content=(
                        f"purpose: {purpose} expected behavior: {expected_behavior}"
                    ),
                ),
            ),
        )
