# Guarded AI triage

The AI release adds a LangGraph workflow without giving a model control over
payment rules, files, shell commands or external systems.

## Workflow

```text
FailureBundle
  -> deterministic critical checks
     -> conclusive: return the deterministic TriageResult
     -> inconclusive:
        -> get_failure_context
        -> get_payment_timeline
        -> get_test_definition
        -> model analysis
        -> evidence and human-review guardrails
        -> TriageResult
```

The model never receives the original `FailureBundle`. It receives only
validated `EvidenceItem` objects returned by the three allowlisted tools.

## Read-only tools

- `get_failure_context` returns the assertion and known financial invariant.
- `get_payment_timeline` returns only requested payment IDs and their events.
- `get_test_definition` returns the documented purpose and expected behavior
  for a known test.

Every tool has Pydantic input and output contracts. A mismatched tool name,
evidence source, unknown payment ID or malformed output is rejected before the
model is called.

## Guardrails

- A conclusive deterministic financial result bypasses the model completely.
- The model can cite only evidence IDs returned by the tools.
- An unknown evidence ID invalidates the model response.
- `insufficient_evidence` always requires human review.
- Tool and model failures degrade to a safe human-review result.
- The model has no shell, file write, test mutation or release action.

## Offline demonstration

The default command needs no API key or network. Ambiguous cases are safely
escalated instead of pretending that an AI diagnosis was made.

```bash
uv run python -m payment_qa_agent.agent examples/duplicate_payment.json
uv run python -m payment_qa_agent.agent examples/completed_to_pending.json
uv run python -m payment_qa_agent.agent examples/insufficient_evidence.json
```

## Manual OpenAI demonstration

Set the API key outside the repository and select the provider explicitly:

```bash
export OPENAI_API_KEY="..."
uv run python -m payment_qa_agent.agent \
  examples/insufficient_evidence.json \
  --provider openai \
  --model gpt-4.1-mini
```

The repository never stores the API key. Unit tests use fake models and never
make network requests.

## Deliberate limitations

This MVP uses local example bundles and a small in-memory test-definition
catalogue. It does not collect CI artifacts automatically, query production
logs, create bug reports, modify tests or decide whether a release may proceed.
