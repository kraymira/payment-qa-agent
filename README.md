# Payment QA Agent

A payment QA demo covering idempotent payment creation, valid state transitions, concurrent requests and controlled failure triage.

The payment service is a small system under test. Financial rules are checked deterministically; an optional AI workflow helps inspect ambiguous failures through three read-only evidence tools.

## What to inspect

- [`tests/test_payment_creation.py`](tests/test_payment_creation.py) — repeated requests, conflicting payloads and concurrent creation.
- [`tests/test_payment_state_machine.py`](tests/test_payment_state_machine.py) — allowed transitions and terminal states.
- [`tests/test_payment_api.py`](tests/test_payment_api.py) — HTTP-boundary integration tests with HTTPX.
- [`tests/test_agent_workflow.py`](tests/test_agent_workflow.py) — deterministic precedence, invalid evidence and safe failure handling.
- [`k6/concurrent_idempotency.js`](k6/concurrent_idempotency.js) — a concurrent HTTP scenario against a running API.

## Quick start

Requires Python 3.12+ and uv. The default demo needs no API key.

    git clone https://github.com/kraymira/payment-qa-agent.git
    cd payment-qa-agent
    uv sync --frozen --group dev
    uv run --frozen pytest

After cloning, `uv run --frozen pytest` is the single command for the automated Python suite.

    uv run --frozen python -m payment_qa_agent.triage examples/duplicate_payment.json
    uv run --frozen python -m payment_qa_agent.agent examples/insufficient_evidence.json

The first command identifies a deterministic idempotency violation. The second collects evidence offline and requests human review.

## Architecture

    HTTPX / k6 -> FastAPI -> PaymentService -> in-memory payments and timeline
                               |
                               +-> validation and explicit state transitions

    FailureBundle -> deterministic rules -> conclusive result
                          |
                          +-> read-only evidence tools -> model or offline fallback
                                                           |
                                                           +-> reference validation -> triage result

## Scope and limitations

- The service stores synthetic payments in memory and supports one process. Its lock does not provide database or multi-worker guarantees.
- Currency validation currently checks the shape of a three-letter code; supported currencies and decimal precision are not yet a complete financial policy.
- The API exposes create/read operations. State transitions are exercised at the service layer.
- This version has no browser UI, real payment provider, webhook delivery, durable storage or ledger reconciliation.
- AI guardrails validate evidence references and selected review conditions. They do not prove that an explanation follows from the evidence; model output must be reviewed by a human.
- No CI workflow is included in this version. Local test results are not a claim of a successful GitHub Actions run.

## Risk and test matrix

| Risk | Expected control | Automated evidence |
| --- | --- | --- |
| A client repeats a request | Same key and payload return the same payment | [Creation tests](tests/test_payment_creation.py) |
| A key is reused with a different amount or currency | Reject the conflict; HTTP boundary returns 409 | [Creation tests](tests/test_payment_creation.py), [API tests](tests/test_payment_api.py) |
| Concurrent retries race | One key resolves to one payment ID | Threaded creation test, concurrent HTTPX test and [k6 scenario](k6/concurrent_idempotency.js) |
| A terminal payment regresses | Reject the invalid state transition | [State-machine tests](tests/test_payment_state_machine.py) |
| Malformed payment data is accepted | Reject non-positive/non-finite amounts, malformed currency codes and blank keys | [Creation tests](tests/test_payment_creation.py); selected HTTP-boundary cases in [API tests](tests/test_payment_api.py) |
| A model overrides a deterministic financial result | Skip tools and model for conclusive deterministic rules | [Agent workflow tests](tests/test_agent_workflow.py) |
| A model invents an evidence reference | Return a human-review fallback | [Agent workflow tests](tests/test_agent_workflow.py) |
| Model or tool processing fails | Preserve a safe human-review result | [Agent workflow tests](tests/test_agent_workflow.py) |

## Run the HTTP concurrency example

Start the API in one terminal:

```bash
uv run --frozen uvicorn payment_qa_agent.api:app --host 127.0.0.1 --port 8000
```

Install [k6](https://grafana.com/docs/k6/latest/set-up/install-k6/) separately, then run in a second terminal from the repository root:

```bash
./scripts/run-k6.sh
```

The scenario sends 20 parallel requests with one idempotency key, checks that every response succeeds with the same payment ID, and writes `artifacts/k6-summary.json`. This is a concurrency correctness check, not a sustained-load benchmark. The Python suite also tests concurrency without requiring k6.

## Failure triage examples

| Bundle | Expected default result |
| --- | --- |
| [duplicate_payment.json](examples/duplicate_payment.json) | `product_bug`: one key is reported to have produced multiple payments |
| [completed_to_pending.json](examples/completed_to_pending.json) | `product_bug`: a completed payment returned to pending |
| [insufficient_evidence.json](examples/insufficient_evidence.json) | `insufficient_evidence`, with human review required |

All bundles are synthetic fixtures. Classification relies on the validated facts supplied by the caller; it does not independently collect production evidence.

The optional model-backed demonstration reads `OPENAI_API_KEY` from the environment and runs only when `--provider openai` is explicitly selected. Never commit keys or real customer data. Unit tests use fake models.

## Design notes

- [Deterministic triage rules](docs/deterministic-triage-rules.md)
- [Guarded AI workflow and tool boundaries](docs/guarded-ai-triage.md)
- [HTTP contract and k6 scenario](docs/payment-api-k6.md)
- [Test strategy](docs/test-strategy.md)
- [Deferred improvements](TODO.md)
- [Original Russian project plan](PROJECT_PLAN_RU.md)

