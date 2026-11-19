# Deferred portfolio improvements

Status: planned, not implemented. Updated 19 November 2026. This checklist is a roadmap; it does not describe current coverage.

## First fix in the existing project

- [ ] Force human review for every result produced on the model path, even when the model selects a conclusive category and cites an existing evidence ID.
- [ ] Add a regression test: ambiguous input plus an unsupported model conclusion must require human review. Preserve the separate deterministic path.
- [ ] Define supported currencies and currency precision before adding corresponding negative tests.
- [ ] Extend HTTP-boundary checks for malformed currency, blank key, unknown payment and extra fields.
- [ ] Add a credential-free GitHub Actions Python job with frozen dependencies, pytest and JUnit artifacts. Verify Python 3.12.
- [ ] Introduce and validate lint/type rules, then make them CI gates.
- [ ] Run the k6 scenario against a local server and keep its concurrency evidence separate from performance claims.

## Playwright and TypeScript checkout companion

Create this small companion only when work is resumed; do not build another payment engine.

- [ ] Reuse a pinned version of this local FastAPI service as the system under test.
- [ ] Add a minimal checkout page with amount/currency, submit, payment ID/status and readable errors. No real cards, wallet or provider credentials.
- [ ] Add typed API helpers, isolated test instances/data and unique keys per independent test.
- [ ] Cover create/read, identical retry, conflicting payload, invalid amount, missing key, unknown payment and concurrent retries.
- [ ] Test UI double-submit behavior with API evidence, not just a disabled button.
- [ ] Test an uncertain network result followed by retry of the same logical request using the same key.
- [ ] Separate mocked browser-network tests from actual local HTTP integration tests.
- [ ] Add TypeScript checks, GitHub Actions, HTML/JUnit reports and failure screenshots/traces; preserve first-attempt failures.
- [ ] Document one-command local execution after dependency/browser installation and risk-based CI gates.
- [ ] Update profile README/pins only after a reproducible reviewed result exists.

Target scope: approximately 8–12 selected UI/API scenarios. Proposed companion name: payment-checkout-playwright. No repository or implementation exists yet.

## Later, only after the small suite is stable

- [ ] Mock provider and webhook delivery with duplicate/out-of-order events.
- [ ] Bounded retries, persistent state and reconciliation.
- [ ] Consider a wallet demonstration only if it adds a clear recruiting signal.

Do not copy employer code, credentials, logs or customer data into this work.
