# Payment QA Agent

A small learning and portfolio project for an AI-Native QA Automation Engineer role.

The project starts with deterministic payment rules and evolves into a guarded AI workflow for test-failure triage. Financial rules remain deterministic; AI may collect evidence and explain a probable cause, but it cannot change tests or approve a release.

The detailed Russian plan is in [`PROJECT_PLAN_RU.md`](PROJECT_PLAN_RU.md).

## Current release: Payment API and concurrent idempotency

Implemented:

- immutable payment and timeline-event models;
- amount, currency and idempotency-key validation;
- idempotent in-memory payment creation;
- an explicit payment state machine;
- an ordered in-memory transaction timeline;
- validated JSON failure bundles;
- deterministic classification of three failure scenarios;
- evidence-grounded triage results;
- a JSON command-line interface;
- a LangGraph workflow with deterministic checks before model analysis;
- three validated read-only evidence tools;
- evidence and human-review guardrails;
- an offline fallback and an optional OpenAI adapter;
- a minimal FastAPI create/read boundary;
- process-safe in-memory idempotency under concurrent requests;
- HTTPX integration tests and a parallel K6 scenario;
- domain-specific errors and PyTest coverage.

Run:

```bash
uv run python -m payment_qa_agent.triage examples/duplicate_payment.json
uv run python -m payment_qa_agent.agent examples/insufficient_evidence.json
uv run pytest
```

Run the HTTP API and K6 scenario in separate terminals:

```bash
uv run uvicorn payment_qa_agent.api:app --host 127.0.0.1 --port 8000
./scripts/run-k6.sh
```

The human-readable decision table is in
[`docs/deterministic-triage-rules.md`](docs/deterministic-triage-rules.md).
The graph, tool boundaries and safety rules are documented in
[`docs/guarded-ai-triage.md`](docs/guarded-ai-triage.md).
The HTTP contract and concurrency scenario are documented in
[`docs/payment-api-k6.md`](docs/payment-api-k6.md).

## Lean roadmap

1. **Payment Core** — deterministic payment rules. Complete.
2. **Deterministic Triage** — classify three JSON failure examples without an LLM. Complete.
3. **Guarded AI Triage** — use LangGraph and three read-only tools, with deterministic rules taking priority. Complete.
4. **Payment API and K6** — expose idempotent creation over HTTP and prove one
   key produces one payment under concurrent requests. Complete.

LangSmith, CI and persistence remain optional extensions after the MVP.

For a manual model-backed run, set `OPENAI_API_KEY` and pass
`--provider openai`. The default offline mode requires no credentials or
network and escalates ambiguous cases to a human.

## Principles

- Add a dependency only when the current release uses it.
- Keep financial assertions deterministic.
- Require evidence for every triage conclusion.
- Escalate insufficient evidence to a human.
- Keep agent tools narrow and read-only.
