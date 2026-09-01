# ADR-0001 — Zenoh is the single fabric; the bus is the API

Date: 2026-06 (design v5 §2.1–§2.3) · Status: accepted; shape taxonomy superseded by [ADR-0013](0013-reply-envelope.md) (the bus-is-the-API core stands)

## Decision

Every capability — move, set DIO, grab frame, run program, replay-seek — is
expressed as Zenoh keys. Services and the UI never talk to each other
directly; only via the bus. Interaction shapes are fixed:

- **Streams → pub/sub** (best-effort, latest-wins for UI telemetry).
- **Synchronous requests → queryables** (request/reply).
- **Long-running operations → the action pattern** (`wf.core.action`): a
  queryable accepts the goal and returns a `goal_id`; feedback streams on a
  feedback key; the result lands on a result key. Same shape as ROS 2
  actions, in plain Zenoh.
- **Persistent data → the config service**, addressed by key.

## Consequences

- Live / sim / twin / replay become swappable because consumers only see keys.
- The browser is a first-class bus citizen through the Zenoh bridge (validated
  in `web/SPIKE.md`); the UI never gets a private side-channel to a service.
- A new feature that wants an HTTP endpoint, direct socket, or shared file as
  its interface between two of our components is **wrong by default** — the
  one standing exception is ADR-0010 (host API for what the bus cannot do:
  process lifecycle of the bus's own participants).

## Validate new plans against

Does the plan introduce any service-to-service or UI-to-service path that is
not Zenoh keys? If yes, it needs the level of justification ADR-0010 had.
