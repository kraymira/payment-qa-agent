from pathlib import Path

import pytest

from payment_qa_agent import Classification, FailureBundle, classify


EXAMPLES_DIR = Path(__file__).parents[1] / "examples"


def load_bundle(name: str) -> FailureBundle:
    return FailureBundle.model_validate_json(
        (EXAMPLES_DIR / name).read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    ("example", "expected_classification", "requires_human_review"),
    [
        ("duplicate_payment.json", Classification.PRODUCT_BUG, False),
        ("completed_to_pending.json", Classification.PRODUCT_BUG, False),
        (
            "insufficient_evidence.json",
            Classification.INSUFFICIENT_EVIDENCE,
            True,
        ),
    ],
)
# Risk: a known payment failure is assigned the wrong response path.
def test_examples_follow_the_decision_table(
    example: str,
    expected_classification: Classification,
    requires_human_review: bool,
) -> None:
    bundle = load_bundle(example)

    result = classify(bundle)

    assert result.classification is expected_classification
    assert result.requires_human_review is requires_human_review


@pytest.mark.parametrize(
    "example",
    [
        "duplicate_payment.json",
        "completed_to_pending.json",
        "insufficient_evidence.json",
    ],
)
# Risk: a triage explanation cites facts that were not present in the failure.
def test_result_cites_only_existing_evidence(example: str) -> None:
    bundle = load_bundle(example)

    result = classify(bundle)

    assert set(result.evidence_ids) <= bundle.evidence_ids


# Risk: repeated analysis of the same failure produces inconsistent conclusions.
def test_classification_is_deterministic() -> None:
    bundle = load_bundle("duplicate_payment.json")

    first_result = classify(bundle)
    second_result = classify(bundle)

    assert second_result == first_result
