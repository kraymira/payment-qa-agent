# Payment QA Agent

A compact learning and portfolio project for the BVNK AI-Native QA Automation Engineer interview.

The detailed Russian implementation plan, including independently runnable MVP releases and the extended version, is available in [`PROJECT_PLAN_RU.md`](PROJECT_PLAN_RU.md).

## Problem statement

Payment failures are expensive to investigate. A QA engineer often has to correlate test output, API responses, transaction state, logs and recent code changes before deciding whether a failure is a product defect, a flaky test, an environment issue or an expected external failure.

This project builds a small payment sandbox and a guarded AI workflow that triages failed tests. The AI does not decide whether money is correct. Financial behaviour is protected by deterministic Python assertions and explicit invariants.

## What the project demonstrates

- Python and PyTest automation.
- Payment-domain fundamentals.
- API and state-transition testing.
- Idempotency, retries and duplicate prevention.
- Webhook deduplication and out-of-order delivery.
- Decimal-based fees and ledger invariants.
- Structured failure evidence.
- LangGraph orchestration and LangSmith evaluation.
- Guardrails and human escalation.
- K6 performance checks.
- CI quality gates.

## Target workflow

```text
Code change
  -> PyTest payment tests
  -> structured failure bundle
  -> triage agent
       -> inspect failure
       -> inspect transaction timeline
       -> inspect relevant logs
       -> classify probable cause
       -> estimate confidence
  -> deterministic guardrail
       -> draft bug report
       -> request human review
       -> or mark as known infrastructure issue
```

The agent will never change a financial assertion or approve a release by itself.

## Scope

### Phase 1 — deterministic payment core

- Payment model and explicit state machine.
- Idempotent payment creation.
- PyTest coverage for duplicates and conflicting requests.
- Decimal amounts and currency validation.

### Phase 2 — API and asynchronous behaviour

- FastAPI endpoints.
- Retry-safe payment creation.
- Duplicate and out-of-order webhooks.
- Transaction timeline and structured logs.

### Phase 3 — failure triage

- Machine-readable PyTest failure artifact.
- Rule-based baseline classifier.
- LLM provider interface with an offline fake for tests.
- Evidence-based triage report.

### Phase 4 — agentic workflow

- LangGraph state and nodes.
- Tool calls with narrow permissions.
- Confidence threshold and human escalation.
- LangSmith traces, datasets and evaluations.

### Phase 5 — quality gate and load testing

- K6 idempotency and latency scenarios.
- CI pipeline.
- Release recommendation based on deterministic checks plus agent evidence.

## Architecture principles

1. Deterministic code owns financial truth.
2. The agent must cite evidence from supplied artifacts.
3. Tool permissions are read-only during triage.
4. Low-confidence cases are escalated.
5. AI output is evaluated against labelled examples.
6. Every escaped defect becomes a regression test or evaluation case.

## First milestone

The initial implementation contains the payment domain model, an in-memory service and tests proving that an idempotency key cannot create two payments or be reused with a different request.

Run:

```bash
uv run pytest
```
