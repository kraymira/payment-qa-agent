# Deterministic triage rules

This document is the human-readable specification for release 2. The
classifier and its tests must implement the same decisions.

## Input contract

A `FailureBundle` contains facts collected after one failed test:

- `test_name` identifies the failed test;
- `assertion` records the observed mismatch;
- `payment_ids` lists the payments involved in the failure;
- `timeline` contains ordered payment events;
- `invariant` names one supported financial rule, when one is known.

Every bundle is validated before classification. Unknown fields, blank
required strings, duplicate identifiers, unordered events and events for an
unlisted payment and unsupported invariant values are rejected.

## Evidence IDs

The classifier cites facts instead of returning an unsupported conclusion:

| Fact | Evidence ID |
|---|---|
| Assertion | `assertion` |
| Financial invariant | `invariant` |
| Payment | `payment:<payment_id>` |
| Timeline event | `event:<event_id>` |

A result is invalid if it cites an ID that cannot be produced from its input
bundle.

## Decision table

Rules are evaluated from top to bottom.

| Priority | Required evidence | Classification | Human review |
|---|---|---|---|
| 1 | The idempotency invariant and more than one distinct payment ID | `product_bug` | No |
| 2 | A timeline event with `completed → pending` | `product_bug` | No |
| 3 | No deterministic rule matches | `insufficient_evidence` | Yes |

`test_bug` and `infrastructure_issue` are valid result categories, but release
2 does not guess them without a structured, documented signal. New rules must
add that signal to the input contract, this table and the automated tests.

## Determinism

Classification depends only on the validated bundle. It does not use the
network, current time, random values, mutable global state or an LLM. The same
bundle therefore produces the same `TriageResult`.
