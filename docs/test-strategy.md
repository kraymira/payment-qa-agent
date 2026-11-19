# Payment QA test strategy

## Scope

This repository demonstrates synthetic payment-domain rules, a small HTTP API and controlled failure triage. It does not process real money. The current automated suite uses Python/pytest; there is no browser suite or CI workflow yet.

## Risks and test selection

The highest-priority risks are duplicate payment creation on retries, conflicting reuse of a key, invalid money input, invalid state transitions and unsupported AI conclusions. Domain tests exercise normalization, finite positive Decimal amounts, idempotency and the state table. HTTPX tests exercise the FastAPI boundary, including concurrent requests and 409/422 responses. The k6 scenario separately checks the same idempotency invariant over a running local HTTP server.

Use the README risk matrix to locate each test. A passing HTTP status alone is insufficient: repeated requests must return the same payment identity; conflicting requests must preserve the original operation.

## Isolation and determinism

Tests create their own PaymentService or API instance. Fixed keys are scoped to those instances, not to shared remote state. Creation uses UUIDs and timestamps; tests verify relationships and invariants instead of snapshotting random identifiers. Failure-classification examples are fixed JSON bundles. Fake and failing models exercise the model boundary without credentials, costs or model-service availability.

The RLock protects a complete lookup/check/write operation inside one process. Thread and ASGI tests do not establish correctness across multiple processes or database nodes.

## AI review boundary

Deterministic conclusive rules take precedence and bypass the model. The model receives only evidence returned by three allowlisted read-only tools. Output checks reject unknown evidence references and malformed tool output, and enforce human review for insufficient-evidence results.

These checks do not establish that a conclusion follows from cited evidence. Until stronger structured checks exist, every model diagnosis must be reviewed by a person. Mandatory human-review enforcement for all model-path results is recorded in TODO.md; it is not implemented in this documentation update.

## Execution and evidence

Run `uv sync --frozen --group dev`, then `uv run --frozen pytest`. For a machine-readable local result, run `uv run --frozen pytest --junitxml=artifacts/pytest-results.xml` after creating `artifacts/`. Keep generated artifacts out of git.

Before publishing code changes, require the Python suite to pass without model API calls. CI/JUnit publication and lint/type gates are planned, not current capabilities. Do not describe a local pass as a GitHub Actions pass.

## Coverage limits

No UI double-submit control, provider timeout recovery, webhook delivery/deduplication, persistent ledger, reconciliation, authentication or multi-worker safety is covered. The HTTP API exposes create/read operations; state transitions are tested directly at the service layer. Currency validation currently checks a three-letter ASCII shape, not membership in an approved currency list or currency-specific precision.
