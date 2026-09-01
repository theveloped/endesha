# ADR-0002 — One key space; the backend is never in the key; replay is a realm

Date: 2026-06 (design v5 §2.2), amended by the selectable-source refactor
(2026-08) · Status: accepted, implemented

## Decision

Design v5 originally proposed realms `live` / `sim` / `replay/<id>` as the
first key segment. The selectable-source refactor superseded half of that:
**the operating namespace is a single fixed token (`cell`)**, and whether a
device is served live, simulated, or replayed is **not encoded in any key**
(see the `wf/core/keys.py` docstring, which is normative). A consumer
cannot tell from a key whether a device is real — that is what lets one
session mix sources per device (ADR-0006).

What survives from the realm idea:

- `replay/<session-id>` is a true second namespace for whole-session
  replay; the same UI renders it by prefix swap alone.
- **Realm-scoped = recorded.** Everything published under the namespace
  prefix is captured by the recorder and comes back verbatim in replay.
  `config/**` and `recording/**` are deliberately realm-less: config is
  shared truth with provenance (ADR-0012), recorder control must not
  record itself.

## Consequences

- Record/replay of any new feature is free *iff* its data lives under the
  realm prefix — and silently missing from recordings if it doesn't.
- No consumer may branch on "is this sim?"; if behaviour must differ, that
  difference belongs in the provider behind the contract.
- Legacy `"live"` defaults still linger in a few corners (conformance
  conftests, recorder defaults) — tracked as a seam in architecture.md §12.

## Validate new plans against

- Does every new runtime topic sit under the realm prefix? If not, is it
  genuinely config (provenance, realm-less) rather than state?
- Does any key or consumer encode/branch on live-vs-sim? That reverses
  this decision.
- Does the plan work when the prefix is `replay/<id>`?
