import json
from pathlib import Path

import pytest

from payment_qa_agent.triage import main


EXAMPLES_DIR = Path(__file__).parents[1] / "examples"


# Risk: the documented CLI does not return machine-readable output.
def test_cli_prints_json_result(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([str(EXAMPLES_DIR / "duplicate_payment.json")])

    output = capsys.readouterr()
    result = json.loads(output.out)

    assert exit_code == 0
    assert result["classification"] == "product_bug"
    assert result["requires_human_review"] is False
    assert output.err == ""


# Risk: an invalid bundle produces an unstructured traceback for automation.
def test_cli_reports_invalid_bundle_as_json(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    invalid_bundle = tmp_path / "invalid.json"
    invalid_bundle.write_text("{}", encoding="utf-8")

    exit_code = main([str(invalid_bundle)])

    output = capsys.readouterr()
    error = json.loads(output.err)

    assert exit_code == 2
    assert error["error"] == "invalid_failure_bundle"
    assert output.out == ""
