# ADR-0013 — Five interaction shapes; one reply envelope

Date: 2026-09-01 (wire-contract RFC, reviewed) · Status: accepted,
implementation in progress (dio, tags, control, washer commands, program runner landed) · Supersedes the
shape taxonomy of [ADR-0001](0001-zenoh-bus-is-the-api.md) (its
bus-is-the-API core stands)

## Decision

The interaction taxonomy is **two primitives and three codified
compositions**: stream (pub/sub), retained value (pub latest-wins + a
queryable answering the *identical* payload), query/reply, action
(query → goal + feedback stream + retained result), config (gated
query/reply write + durable retained read).

Every command/request queryable speaks **one envelope**
(`wf.core.envelope` / `web/src/lib/envelope.ts`):

- request: `{req_id (client-minted UUIDv7), client_id?, args}` —
  `req_id` makes resubmission idempotent on every command, not just
  actions; providers keep a recent-replies ring.
- reply: `{ok: true, value}` | `{ok: true, goal}` | `{ok: false, error}`.
  `value` is always present on ok (`{}` if empty). `goal` is fully closed
  and self-describing: it carries `feedback_key`/`result_key`/`cancel_key`
  (clients build no keys by convention) plus `state` and `result_ttl_s`;
  the goal id is the adopted `req_id`. `error` is
  `{code, reason, detail?, retryable?}` with `code` from the closed
  8-value enum (adding a code is an ADR-level event) and `reason` from
  the contract's registered `ERROR_REASONS`.
- Retained reads are **not** enveloped: querying a retained key returns
  exactly the published payload. Streams are untouched (no wrapper at
  200 Hz).

The generic client is `call()`: value now, or transparently follow the
goal's retained result (recursively the envelope), or raise/throw a typed
error — so an operation can move from sync to goal-shaped without
breaking a caller. `QueryAudit` reads `ok` from the envelope; the
ok/accepted sniffing heuristic is deleted.

## Consequences

- One code path for audit, proxies, retries, conformance; error handling
  is enumerable and testable (`retryable` enables domain-blind retries).
- Wire-breaking for request/reply; migration is contract-by-contract
  behind conformance suites (no backwards compatibility — RFC review
  decision 6). Recorded streams replay unchanged.
- The wire-level uniformity is not semantic ignorance: contracts still
  fix per key whether it is cancellable/goal-shaped; the envelope makes
  it discoverable, not optional to know.

## Validate new plans against

- Does every new queryable reply in the envelope, with registered
  reasons? Does its conformance suite assert that?
- Does any client build goal follow-keys by convention instead of using
  the reply's keys?
- Is anything long-running modeled as a plain query (loses cancel), or
  anything atomic as a goal (needless lifecycle)?
