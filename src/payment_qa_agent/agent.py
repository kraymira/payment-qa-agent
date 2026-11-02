"""Guarded LangGraph workflow and command-line interface for AI triage."""

import argparse
import json
import operator
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, Protocol, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from payment_qa_agent.agent_models import (
    AgentAnalysisContext,
    AgentRun,
    EvidenceItem,
    FailureContextQuery,
    PaymentTimelineQuery,
    TestDefinitionQuery,
    ToolEvidence,
    ToolName,
)
from payment_qa_agent.agent_tools import AgentToolbox, ReadOnlyToolbox
from payment_qa_agent.classifier import classify
from payment_qa_agent.triage import load_failure_bundle
from payment_qa_agent.triage_models import (
    Classification,
    FailureBundle,
    TriageResult,
)


class TriageModel(Protocol):
    """Small model boundary that is easy to fake in unit tests."""

    def analyze(self, context: AgentAnalysisContext) -> TriageResult: ...


class HumanReviewModel:
    """Offline fallback that never pretends to have made an AI diagnosis."""

    def analyze(self, context: AgentAnalysisContext) -> TriageResult:
        evidence_ids = ["assertion"]
        definition_id = f"test_definition:{context.test_name}"
        if definition_id in context.evidence_ids:
            evidence_ids.append(definition_id)
        return TriageResult(
            classification=Classification.INSUFFICIENT_EVIDENCE,
            probable_cause=(
                "offline mode collected evidence but requires model or human analysis"
            ),
            evidence_ids=evidence_ids,
            requires_human_review=True,
        )


class OpenAITriageModel:
    """Optional real-model adapter used only for a manual demonstration."""

    def __init__(self, model_name: str) -> None:
        self._model = ChatOpenAI(model=model_name, temperature=0)

    def analyze(self, context: AgentAnalysisContext) -> TriageResult:
        structured_model = self._model.with_structured_output(TriageResult)
        response = structured_model.invoke(
            [
                SystemMessage(
                    content=(
                        "You triage payment test failures. Use only the supplied "
                        "evidence and cite only its evidence_id values. Never "
                        "weaken a financial invariant. Choose product_bug, "
                        "test_bug, infrastructure_issue, or "
                        "insufficient_evidence. If facts are incomplete, set "
                        "requires_human_review to true. Keep probable_cause "
                        "short and concrete."
                    )
                ),
                HumanMessage(content=context.model_dump_json(indent=2)),
            ]
        )
        return TriageResult.model_validate(response)


class AgentState(TypedDict, total=False):
    """Internal state passed between LangGraph nodes."""

    bundle: FailureBundle
    baseline: TriageResult
    evidence: Annotated[list[EvidenceItem], operator.add]
    tool_calls: Annotated[list[ToolName], operator.add]
    guardrail_errors: Annotated[list[str], operator.add]
    model_result: TriageResult
    result: TriageResult
    used_model: bool


def build_triage_graph(
    model: TriageModel,
    toolbox: AgentToolbox | None = None,
):
    """Build a graph whose only side-effecting boundary is the model call."""

    evidence_tools = toolbox or ReadOnlyToolbox()

    def deterministic_check(state: AgentState) -> AgentState:
        return {"baseline": classify(state["bundle"])}

    def route_after_deterministic(state: AgentState) -> str:
        if state["baseline"].classification is Classification.INSUFFICIENT_EVIDENCE:
            return "collect_failure_context"
        return "use_deterministic_result"

    def use_deterministic_result(state: AgentState) -> AgentState:
        return {"result": state["baseline"], "used_model": False}

    def collect_failure_context(state: AgentState) -> AgentState:
        bundle = state["bundle"]
        query = FailureContextQuery(test_name=bundle.test_name)
        return _collect_tool_evidence(
            expected_tool=ToolName.FAILURE_CONTEXT,
            call=lambda: evidence_tools.get_failure_context(query, bundle),
        )

    def collect_payment_timeline(state: AgentState) -> AgentState:
        bundle = state["bundle"]
        query = PaymentTimelineQuery(payment_ids=tuple(bundle.payment_ids))
        return _collect_tool_evidence(
            expected_tool=ToolName.PAYMENT_TIMELINE,
            call=lambda: evidence_tools.get_payment_timeline(query, bundle),
        )

    def collect_test_definition(state: AgentState) -> AgentState:
        query = TestDefinitionQuery(test_name=state["bundle"].test_name)
        return _collect_tool_evidence(
            expected_tool=ToolName.TEST_DEFINITION,
            call=lambda: evidence_tools.get_test_definition(query),
        )

    def analyze_with_model(state: AgentState) -> AgentState:
        if state.get("guardrail_errors"):
            return {"used_model": False}
        try:
            context = AgentAnalysisContext(
                test_name=state["bundle"].test_name,
                evidence=tuple(state.get("evidence", [])),
            )
            result = TriageResult.model_validate(model.analyze(context))
        # A provider may raise its own exception type; every failure must fail safe.
        except Exception as error:  # noqa: BLE001
            return {
                "guardrail_errors": [f"model_error: {error}"],
                "used_model": True,
            }
        return {"model_result": result, "used_model": True}

    def validate_model_result(state: AgentState) -> AgentState:
        evidence = tuple(state.get("evidence", []))
        result = state.get("model_result")
        if result is None:
            return {
                "result": _safe_human_review_result(
                    state["bundle"],
                    "agent could not produce a validated conclusion",
                )
            }

        available_ids = {item.evidence_id for item in evidence}
        unknown_ids = set(result.evidence_ids) - available_ids
        if unknown_ids:
            joined = ", ".join(sorted(unknown_ids))
            return {
                "guardrail_errors": [f"model cited unknown evidence IDs: {joined}"],
                "result": _safe_human_review_result(
                    state["bundle"],
                    "model response failed evidence validation",
                ),
            }

        if (
            result.classification is Classification.INSUFFICIENT_EVIDENCE
            and not result.requires_human_review
        ):
            return {
                "guardrail_errors": ["insufficient evidence must require human review"],
                "result": _safe_human_review_result(
                    state["bundle"],
                    "model response failed human-review validation",
                ),
            }
        return {"result": result}

    graph = StateGraph(AgentState)
    graph.add_node("deterministic_check", deterministic_check)
    graph.add_node("use_deterministic_result", use_deterministic_result)
    graph.add_node("collect_failure_context", collect_failure_context)
    graph.add_node("collect_payment_timeline", collect_payment_timeline)
    graph.add_node("collect_test_definition", collect_test_definition)
    graph.add_node("analyze_with_model", analyze_with_model)
    graph.add_node("validate_model_result", validate_model_result)

    graph.add_edge(START, "deterministic_check")
    graph.add_conditional_edges(
        "deterministic_check",
        route_after_deterministic,
        {
            "use_deterministic_result": "use_deterministic_result",
            "collect_failure_context": "collect_failure_context",
        },
    )
    graph.add_edge("use_deterministic_result", END)
    graph.add_edge("collect_failure_context", "collect_payment_timeline")
    graph.add_edge("collect_payment_timeline", "collect_test_definition")
    graph.add_edge("collect_test_definition", "analyze_with_model")
    graph.add_edge("analyze_with_model", "validate_model_result")
    graph.add_edge("validate_model_result", END)
    return graph.compile()


def run_guarded_triage(
    bundle: FailureBundle,
    model: TriageModel | None = None,
    toolbox: AgentToolbox | None = None,
) -> AgentRun:
    """Run guarded triage and return its result with audit metadata."""

    graph = build_triage_graph(model or HumanReviewModel(), toolbox)
    state = graph.invoke(
        {
            "bundle": bundle,
            "evidence": [],
            "tool_calls": [],
            "guardrail_errors": [],
            "used_model": False,
        }
    )
    return AgentRun(
        result=state["result"],
        tool_calls=tuple(state.get("tool_calls", [])),
        guardrail_errors=tuple(state.get("guardrail_errors", [])),
        used_model=state.get("used_model", False),
    )


def _collect_tool_evidence(*, expected_tool: ToolName, call) -> AgentState:
    try:
        output = ToolEvidence.model_validate(call())
        if output.tool is not expected_tool:
            raise ValueError(f"expected {expected_tool}, received {output.tool}")
    # Toolbox implementations are an external boundary with unknown exceptions.
    except Exception as error:  # noqa: BLE001
        return {
            "tool_calls": [expected_tool],
            "guardrail_errors": [f"{expected_tool}: {error}"],
        }
    return {
        "evidence": list(output.items),
        "tool_calls": [expected_tool],
    }


def _safe_human_review_result(
    bundle: FailureBundle,
    probable_cause: str,
) -> TriageResult:
    return TriageResult(
        classification=Classification.INSUFFICIENT_EVIDENCE,
        probable_cause=probable_cause,
        evidence_ids=["assertion"],
        requires_human_review=True,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run guarded triage with a safe offline default or an OpenAI model."""

    parser = argparse.ArgumentParser(
        description="Triage a payment failure with a guarded LangGraph workflow.",
    )
    parser.add_argument("bundle", type=Path, help="path to a failure bundle")
    parser.add_argument(
        "--provider",
        choices=("offline", "openai"),
        default="offline",
        help="model provider; offline always escalates ambiguous cases",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("PAYMENT_QA_MODEL", "gpt-4.1-mini"),
        help="OpenAI model name used with --provider openai",
    )
    arguments = parser.parse_args(argv)

    try:
        bundle = load_failure_bundle(arguments.bundle)
    except (OSError, ValidationError) as error:
        print(
            json.dumps(
                {
                    "error": "invalid_failure_bundle",
                    "message": str(error),
                }
            ),
            file=sys.stderr,
        )
        return 2

    if arguments.provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            print(
                json.dumps(
                    {
                        "error": "missing_api_key",
                        "message": ("OPENAI_API_KEY is required for --provider openai"),
                    }
                ),
                file=sys.stderr,
            )
            return 2
        model: TriageModel = OpenAITriageModel(arguments.model)
    else:
        model = HumanReviewModel()

    run = run_guarded_triage(bundle, model=model)
    print(run.result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
