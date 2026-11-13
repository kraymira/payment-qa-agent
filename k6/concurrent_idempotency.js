import http from "k6/http";
import { check } from "k6";

const concurrentRequests = Number(__ENV.CONCURRENT_REQUESTS || 20);

export const options = {
  scenarios: {
    concurrent_idempotency: {
      executor: "shared-iterations",
      vus: 1,
      iterations: 1,
      maxDuration: "30s",
    },
  },
  batch: concurrentRequests,
  batchPerHost: concurrentRequests,
  thresholds: {
    checks: ["rate==1"],
    http_req_failed: ["rate==0"],
  },
};

export default function () {
  const baseUrl = (__ENV.BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  const idempotencyKey =
    __ENV.IDEMPOTENCY_KEY || `k6-concurrent-${Date.now()}`;
  const body = JSON.stringify({ amount: "19.99", currency: "EUR" });
  const params = {
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
  };
  const requests = Array.from({ length: concurrentRequests }, () => [
    "POST",
    `${baseUrl}/payments`,
    body,
    params,
  ]);

  const responses = http.batch(requests);
  const paymentIds = responses
    .filter((response) => response.status === 201)
    .map((response) => response.json("payment_id"));

  check(responses, {
    "all concurrent requests succeed": (items) =>
      items.length === concurrentRequests &&
      items.every((response) => response.status === 201),
    "all responses contain a payment ID": () =>
      paymentIds.length === concurrentRequests &&
      paymentIds.every((paymentId) => typeof paymentId === "string"),
    "one idempotency key creates exactly one payment": () =>
      new Set(paymentIds).size === 1,
  });
}

export function handleSummary(data) {
  return {
    stdout: "K6 summary written to artifacts/k6-summary.json\n",
    "artifacts/k6-summary.json": JSON.stringify(data, null, 2),
  };
}
