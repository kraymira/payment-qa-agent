import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from payment_qa_agent import FailureBundle


EXAMPLES_DIR = Path(__file__).parents[1] / "examples"


def load_example(name: str) -> dict[str, object]:
    return json.loads((EXAMPLES_DIR / name).read_text(encoding="utf-8"))


# Risk: malformed failure data reaches the classifier and produces a plausible answer.
def test_all_example_bundles_match_the_input_contract() -> None:
    for path in EXAMPLES_DIR.glob("*.json"):
        bundle = FailureBundle.model_validate_json(
            path.read_text(encoding="utf-8")
        )

        assert bundle.test_name
        assert "assertion" in bundle.evidence_ids


# Risk: a producer silently changes the JSON contract without updating triage.
def test_unknown_bundle_field_is_rejected() -> None:
    data = load_example("duplicate_payment.json")
    data["unexpected"] = "new producer field"

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        FailureBundle.model_validate(data)


# Risk: free-form invariant text is mistaken for a financial rule the tool knows.
def test_unsupported_invariant_is_rejected() -> None:
    data = load_example("duplicate_payment.json")
    data["invariant"] = "payments should probably look right"

    with pytest.raises(ValidationError, match="Input should be"):
        FailureBundle.model_validate(data)


# Risk: duplicated identifiers are mistaken for two independent payments.
def test_duplicate_payment_ids_are_rejected() -> None:
    data = load_example("duplicate_payment.json")
    data["payment_ids"] = ["pay_1", "pay_1"]

    with pytest.raises(ValidationError, match="payment_ids must be unique"):
        FailureBundle.model_validate(data)


# Risk: a timeline event is cited for a payment absent from the evidence bundle.
def test_timeline_for_unlisted_payment_is_rejected() -> None:
    data = load_example("completed_to_pending.json")
    timeline = data["timeline"]
    assert isinstance(timeline, list)
    timeline[0]["payment_id"] = "pay_unknown"

    with pytest.raises(ValidationError, match="pay_unknown"):
        FailureBundle.model_validate(data)


# Risk: event order is corrupted and changes the apparent payment history.
def test_unordered_timeline_is_rejected() -> None:
    data = load_example("completed_to_pending.json")
    timeline = data["timeline"]
    assert isinstance(timeline, list)
    data["timeline"] = list(reversed(timeline))

    with pytest.raises(ValidationError, match="ordered by occurred_at"):
        FailureBundle.model_validate(data)


# Risk: a timestamp without a timezone is ordered differently across machines.
def test_timeline_timestamp_without_timezone_is_rejected() -> None:
    data = load_example("completed_to_pending.json")
    timeline = data["timeline"]
    assert isinstance(timeline, list)
    timeline[0]["occurred_at"] = "2026-10-25T09:00:00"

    with pytest.raises(ValidationError, match="must include a timezone"):
        FailureBundle.model_validate(data)
