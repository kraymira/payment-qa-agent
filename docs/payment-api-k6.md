# Payment API and concurrent idempotency test

The HTTP extension exposes the existing payment-domain rules without moving
them into route handlers.

## Endpoints

- `GET /health`
- `POST /payments` with a required `Idempotency-Key` header
- `GET /payments/{payment_id}`

The API returns `409 Conflict` when one key is reused with a different amount
or currency. Invalid amounts, currencies and empty keys return `422`.

## Why the service now uses a lock

The original in-memory implementation performed a lookup and then a write as
separate operations. Two server threads could both observe a missing key and
create different payments. `PaymentService` now protects each complete
read-check-write operation with one re-entrant lock.

This is correct for one Python process. It is not a substitute for a database
unique constraint when multiple processes or machines serve requests.

## Run the API

```bash
uv run uvicorn payment_qa_agent.api:app --host 127.0.0.1 --port 8000
```

## Run K6

Install K6 separately, keep the API running, and execute:

```bash
./scripts/run-k6.sh
```

The test sends 20 parallel `POST /payments` requests with one idempotency key.
It fails unless every response succeeds and all responses contain the same
payment ID. The full K6 summary is written to `artifacts/k6-summary.json`.

The concurrency can be changed without editing the script:

```bash
CONCURRENT_REQUESTS=50 ./scripts/run-k6.sh
```

The accompanying HTTPX integration test exercises the same race entirely in
process and therefore runs in the normal PyTest suite even when K6 is not
installed.
