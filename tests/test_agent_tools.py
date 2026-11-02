from pathlib import Path

import pytest

from payment_qa_agent import FailureBundle
from payment_qa_agent.agent_models import (
    FailureContextQuery,
    PaymentTimelineQuery,
    ToolName,
)
from payment_qa_agent.agent_models import (
    TestDefinitionQuery as DefinitionQuery,
)
from payment_qa_agent.agent_tools import ReadOnlyToolbox

EXAMPLES_DIR = Path(__file__).parents[1] / "examples"


def load_bundle(name: str) -> FailureBundle:
    return FailureBundle.model_validate_json(
        (EXAMPLES_DIR / name).read_text(encoding="utf-8")
    )


# Risk: a tool exposes unrelated failure data instead of the requested test.
def test_failure_context_rejects_a_different_test_name() -> None:
    bundle = load_bundle("duplicate_payment.json")

    with pytest.raises(ValueError, match="does not match"):
        ReadOnlyToolbox().get_failure_context(
            FailureContextQuery(test_name="test_other_payment"),
            bundle,
        )


# Risk: the agent retrieves events for a payment outside the validated bundle.
def test_timeline_tool_rejects_unknown_payment_ids() -> None:
    bundle = load_bundle("completed_to_pending.json")

    with pytest.raises(ValueError, match="pay_unknown"):
        ReadOnlyToolbox().get_payment_timeline(
            PaymentTimelineQuery(payment_ids=("pay_unknown",)),
            bundle,
        )


# Risk: a model invents expected behavior because no test definition was found.
def test_unknown_test_definition_returns_no_evidence() -> None:
    evidence = ReadOnlyToolbox().get_test_definition(
        DefinitionQuery(test_name="test_unknown")
    )

    assert evidence.tool is ToolName.TEST_DEFINITION
    assert evidence.items == ()


# Risk: the test definition cannot be identified and cited independently.
def test_known_test_definition_has_a_stable_evidence_id() -> None:
    evidence = ReadOnlyToolbox().get_test_definition(
        DefinitionQuery(test_name="test_provider_response")
    )

    assert [item.evidence_id for item in evidence.items] == [
        "test_definition:test_provider_response"
    ]
