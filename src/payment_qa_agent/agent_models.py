"""Validated contracts shared by the guarded triage graph and its tools."""

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from payment_qa_agent.triage_models import NonEmptyString, TriageResult


class ToolName(StrEnum):
    """The complete allowlist of tools available to the agent."""

    FAILURE_CONTEXT = "get_failure_context"
    PAYMENT_TIMELINE = "get_payment_timeline"
    TEST_DEFINITION = "get_test_definition"


class EvidenceItem(BaseModel):
    """One immutable fact returned by an allowlisted read-only tool."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: NonEmptyString
    source: ToolName
    content: NonEmptyString


class ToolEvidence(BaseModel):
    """Validated output contract for every agent tool."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: ToolName
    items: tuple[EvidenceItem, ...] = ()

    @model_validator(mode="after")
    def validate_items(self) -> Self:
        """Keep evidence unique and tied to the tool that produced it."""

        evidence_ids = [item.evidence_id for item in self.items]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("tool evidence IDs must be unique")
        if any(item.source is not self.tool for item in self.items):
            raise ValueError("evidence source must match the producing tool")
        return self


class FailureContextQuery(BaseModel):
    """Arguments accepted by ``get_failure_context``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    test_name: NonEmptyString


class PaymentTimelineQuery(BaseModel):
    """Arguments accepted by ``get_payment_timeline``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    payment_ids: tuple[NonEmptyString, ...]

    @model_validator(mode="after")
    def require_unique_payment_ids(self) -> Self:
        if len(self.payment_ids) != len(set(self.payment_ids)):
            raise ValueError("payment_ids must be unique")
        return self


class TestDefinitionQuery(BaseModel):
    """Arguments accepted by ``get_test_definition``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    test_name: NonEmptyString


class AgentAnalysisContext(BaseModel):
    """Only the validated facts that a model may use for its conclusion."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    test_name: NonEmptyString
    evidence: tuple[EvidenceItem, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_evidence(self) -> Self:
        evidence_ids = [item.evidence_id for item in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("agent evidence IDs must be unique")
        return self

    @property
    def evidence_ids(self) -> frozenset[str]:
        return frozenset(item.evidence_id for item in self.evidence)


class AgentRun(BaseModel):
    """Result plus audit metadata useful for tests and demonstrations."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result: TriageResult
    tool_calls: tuple[ToolName, ...]
    guardrail_errors: tuple[str, ...]
    used_model: bool
