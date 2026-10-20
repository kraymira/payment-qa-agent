# Payment QA Agent

A small learning and portfolio project for an AI-Native QA Automation Engineer role.

The project starts with deterministic payment rules and evolves into a guarded AI workflow for test-failure triage. Financial rules remain deterministic; AI may collect evidence and explain a probable cause, but it cannot change tests or approve a release.

The detailed Russian plan is in [`PROJECT_PLAN_RU.md`](PROJECT_PLAN_RU.md).

## Current release: Payment Core

Implemented:

- immutable payment and timeline-event models;
- amount, currency and idempotency-key validation;
- idempotent in-memory payment creation;
- an explicit payment state machine;
- an ordered in-memory transaction timeline;
- domain-specific errors and PyTest coverage.

Run:

```bash
uv run pytest
```

## Lean roadmap

1. **Payment Core** — deterministic payment rules. Complete.
2. **Deterministic Triage** — classify three JSON failure examples without an LLM.
3. **Guarded AI Triage** — use LangGraph and three read-only tools, with deterministic rules taking priority.

HTTP APIs, LangSmith, K6, CI and persistence are optional extensions after the MVP.

## Principles

- Add a dependency only when the current release uses it.
- Keep financial assertions deterministic.
- Require evidence for every triage conclusion.
- Escalate insufficient evidence to a human.
- Keep agent tools narrow and read-only.
