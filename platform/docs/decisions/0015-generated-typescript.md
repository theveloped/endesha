# ADR-0015 — The TypeScript wire mirror is generated from the Python contracts

Date: 2026-09-02 (wire-contract RFC §7, reviewed) · Status: accepted,
implemented for keys + types (adoption tail tracked as a seam)

## Decision

The Python contract packages are the formal source of truth for the wire
(design v5 §2.1's original promise). `wf.tools.wiregen` derives the
TypeScript side from them by introspection — no external IDL, no schema
registry, no build-time codegen pipeline:

- `web/src/lib/gen/keys.ts`: one TS builder per Python key function,
  reconstructed as a template literal by calling the function with
  placeholder tokens (arity and shape cannot drift silently).
- `web/src/lib/gen/types.ts`: TS interfaces for every wire dataclass
  (wire field names, optionality from defaults, ns timestamps as
  `WireTimestamp`), per-contract `ERROR_REASONS`, the envelope `CODES`,
  and `FLOAT_FIELDS` — which fields a write-side CBOR encoder must mark
  as floats (the reason the hand-rolled camera encoder existed).

Generated output is **committed** (reviewable diffs, no build step);
`pixi run wire-check` regenerates and fails on drift, beside
`docs-check` in the pre-commit checks. `web/src/lib/config.ts` is now a
thin hand-written adapter (historical names, RID/CID defaults, grouped
conveniences) whose every body delegates to `gen/keys.ts` — the
hand-maintained key mirror is gone, and the adapter is compiler-checked
against the generated arities.

## Consequences

- A key or message change in Python is caught the moment `wire-check`
  runs; the TS side can no longer lag by hand.
- The escalation path to a formal IDL stays open; nothing here forecloses
  it (RFC §7).
- Remaining tail (a seam, not a decision): `messages.ts` still hand-writes
  the interfaces `gen/types.ts` now also carries; the camera write-side
  CBOR encoder does not yet consume `FLOAT_FIELDS`; the supervisor's
  retained payloads remain untyped.

## Validate new plans against

- Does a new contract or key change regenerate cleanly
  (`pixi run wiregen`) and land the gen diff in the same PR?
- Does any new TS code hand-write a key template or wire interface that
  `gen/` already carries?
