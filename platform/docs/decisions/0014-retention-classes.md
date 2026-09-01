# ADR-0014 — Two retention classes: session-retained vs durable-retained

Date: 2026-09-01 (wire-contract RFC §3.1, reviewed) · Status: accepted

## Decision

Retained state on the bus comes in exactly two classes, and every
retained key belongs to one, explicitly:

- **Session-retained**: lives and dies with its producer's liveliness
  token (device inventory, program state, control owner, log/event
  rings, action results). A consumer that sees the token drop treats the
  value as gone — "authority not alive ⇒ nobody holds the lease",
  generalized.
- **Durable-retained**: survives restarts and exists *only* behind the
  config service's validated, provenance-keeping write path
  ([ADR-0012](0012-config-service-provenance.md)). No producer ever
  publishes durable truth directly onto a retained key.

Consumers follow retained keys through the shared helper
(`wf.core.retained.subscribe_retained` / `bus.subscribeRetained`):
subscribe first, seed with a query second, deltas win over the seed.

## Consequences

- A crashed producer cannot keep asserting stale truth (the MQTT
  retained-message failure mode is structurally excluded).
- Query/subscribe equivalence on retained keys is a conformance
  assertion, not a habit.

## Validate new plans against

- For each new retained key: which class is it, and does its lifetime
  match (liveliness-scoped vs config-gated)?
- Does any producer publish durable state outside the config service?
- Do consumers use the shared helper rather than re-implementing seed
  ordering?
