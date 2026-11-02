from pathlib import Path

import pytest

from payment_qa_agent import (
    Classification,
    FailureBundle,
    TriageResult,
    classify,
)
from payment_qa_agent.agent import run_guarded_triage
from payment_qa_agent.agent_models import AgentAnalysisContext, ToolName
from payment_qa_agent.agent_tools import ReadOnlyToolbox

EXAMPLES_DIR = Path(__file__).parents[1] / "examples"


def load_bundle(name: str) -> FailureBundle:
    return FailureBundle.model_validate_json(
        (EXAMPLES_DIR / name).read_text(encoding="utf-8")
    )


class FakeModel:
    def __init__(self, result: TriageResult) -> None:
        self.result = result
        self.contexts: list[AgentAnalysisContext] = []

    def analyze(self, context: AgentAnalysisContext) -> TriageResult:
        self.contexts.append(context)
        return self.result


class FailingModel:
    def analyze(self, context: AgentAnalysisContext) -> TriageResult:
        raise RuntimeError("model unavailable")


@pytest.mark.parametrize(
    "example",
    ["duplicate_payment.json", "completed_to_pending.json"],
)
# Risk: an LLM weakens a critical financial rule already proved by code.
def test_deterministic_critical_result_skips_tools_and_model(
    example: str,
) -> None:
    bundle = load_bundle(example)
    model = FakeModel(
        TriageResult(
            classification=Classification.TEST_BUG,
            probable_cause="the assertion is wrong",
            evidence_ids=["assertion"],
            requires_human_review=False,
        )
    )

    run = run_guarded_triage(bundle, model=model)

    assert run.result == classify(bundle)
    assert run.tool_calls == ()
    assert run.used_model is False
    assert model.contexts == []


# Risk: the model diagnoses a failure without collecting the allowlisted facts.
def test_ambiguous_failure_collects_all_read_only_evidence() -> None:
    bundle = load_bundle("insufficient_evidence.json")
    model = FakeModel(
        TriageResult(
            classification=Classification.INFRASTRUCTURE_ISSUE,
            probable_cause="provider request exceeded the test timeout",
            evidence_ids=[
                "assertion",
                "test_definition:test_provider_response",
            ],
            requires_human_review=True,
        )
    )

    run = run_guarded_triage(bundle, model=model)

    assert run.result.classification is Classification.INFRASTRUCTURE_ISSUE
    assert run.tool_calls == (
        ToolName.FAILURE_CONTEXT,
        ToolName.PAYMENT_TIMELINE,
        ToolName.TEST_DEFINITION,
    )
    assert run.guardrail_errors == ()
    assert run.used_model is True
    assert len(model.contexts) == 1
    assert model.contexts[0].evidence_ids == {
        "assertion",
        "test_definition:test_provider_response",
    }


# Risk: a plausible AI explanation cites a log or event that was never observed.
def test_unknown_model_evidence_is_rejected() -> None:
    bundle = load_bundle("insufficient_evidence.json")
    model = FakeModel(
        TriageResult(
            classification=Classification.INFRASTRUCTURE_ISSUE,
            probable_cause="network packet loss",
            evidence_ids=["log:invented"],
            requires_human_review=False,
        )
    )

    run = run_guarded_triage(bundle, model=model)

    assert run.result.classification is Classification.INSUFFICIENT_EVIDENCE
    assert run.result.requires_human_review is True
    assert "log:invented" in run.guardrail_errors[0]


# Risk: the model admits evidence is insufficient but suppresses escalation.
def test_insufficient_evidence_always_requires_human_review() -> None:
    bundle = load_bundle("insufficient_evidence.json")
    model = FakeModel(
        TriageResult(
            classification=Classification.INSUFFICIENT_EVIDENCE,
            probable_cause="not enough facts",
            evidence_ids=["assertion"],
            requires_human_review=False,
        )
    )

    run = run_guarded_triage(bundle, model=model)

    assert run.result.requires_human_review is True
    assert "must require human review" in run.guardrail_errors[0]


# Risk: an unavailable model crashes triage and hides the original failure.
def test_model_failure_degrades_to_human_review() -> None:
    run = run_guarded_triage(
        load_bundle("insufficient_evidence.json"),
        model=FailingModel(),
    )

    assert run.result.classification is Classification.INSUFFICIENT_EVIDENCE
    assert run.result.requires_human_review is True
    assert "model unavailable" in run.guardrail_errors[0]


class InvalidToolbox(ReadOnlyToolbox):
    def get_test_definition(self, query):
        return {
            "tool": "get_test_definition",
            "items": [
                {
                    "evidence_id": "test_definition:test_provider_response",
                    "source": "get_failure_context",
                    "content": "mismatched source",
                }
            ],
        }


# Risk: malformed or misattributed tool output reaches the model as trusted data.
def test_invalid_tool_output_is_rejected_before_model_call() -> None:
    model = FakeModel(
        TriageResult(
            classification=Classification.TEST_BUG,
            probable_cause="bad fixture",
            evidence_ids=["assertion"],
            requires_human_review=False,
        )
    )

    run = run_guarded_triage(
        load_bundle("insufficient_evidence.json"),
        model=model,
        toolbox=InvalidToolbox(),
    )

    assert run.result.classification is Classification.INSUFFICIENT_EVIDENCE
    assert run.result.requires_human_review is True
    assert "evidence source" in run.guardrail_errors[0]
    assert run.used_model is False
    assert model.contexts == []


# Risk: the same fake-model run changes between test executions.
def test_fake_model_workflow_is_reproducible() -> None:
    bundle = load_bundle("insufficient_evidence.json")
    result = TriageResult(
        classification=Classification.INFRASTRUCTURE_ISSUE,
        probable_cause="provider timeout",
        evidence_ids=[
            "assertion",
            "test_definition:test_provider_response",
        ],
        requires_human_review=True,
    )

    first = run_guarded_triage(bundle, model=FakeModel(result))
    second = run_guarded_triage(bundle, model=FakeModel(result))

    assert second == first
