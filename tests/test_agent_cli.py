import json
from pathlib import Path

from payment_qa_agent.agent import main

EXAMPLES_DIR = Path(__file__).parents[1] / "examples"


# Risk: guarded triage cannot be demonstrated without credentials or network.
def test_offline_cli_runs_without_an_api_key(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main([str(EXAMPLES_DIR / "insufficient_evidence.json")])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["classification"] == "insufficient_evidence"
    assert output["requires_human_review"] is True


# Risk: a critical deterministic result changes when invoked through the agent CLI.
def test_agent_cli_preserves_deterministic_critical_result(capsys) -> None:
    exit_code = main([str(EXAMPLES_DIR / "duplicate_payment.json")])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["classification"] == "product_bug"
    assert output["requires_human_review"] is False


# Risk: selecting a real provider without credentials causes an opaque traceback.
def test_openai_cli_reports_a_missing_api_key(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    exit_code = main(
        [
            str(EXAMPLES_DIR / "insufficient_evidence.json"),
            "--provider",
            "openai",
        ]
    )

    error = json.loads(capsys.readouterr().err)
    assert exit_code == 2
    assert error["error"] == "missing_api_key"
