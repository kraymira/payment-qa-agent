"""JSON command-line interface for deterministic failure triage."""

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from payment_qa_agent.classifier import classify
from payment_qa_agent.triage_models import FailureBundle


def load_failure_bundle(path: Path) -> FailureBundle:
    """Read and validate one JSON failure bundle from disk."""

    return FailureBundle.model_validate_json(path.read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    """Run deterministic triage for one JSON file."""

    parser = argparse.ArgumentParser(
        description="Classify a payment test failure without an LLM.",
    )
    parser.add_argument("bundle", type=Path, help="path to a failure bundle")
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

    print(classify(bundle).model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
