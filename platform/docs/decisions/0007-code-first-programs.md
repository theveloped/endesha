# ADR-0007 — Programs are code-first python-statemachine statecharts; graphs are derived

Date: 2026-08-15 (program-layer RFC §0) · Status: accepted, implemented

## Decision

Automation programs are code-first `python-statemachine` StateCharts (Vention
"Python application" style). No React Flow authoring, no behaviour trees.
The state graph is **exported from the class** and rendered read-only in the
UI; the code stays the only source of truth. Vision pipelines follow the same
rule (vision RFC §0).

Transition semantics: Vention-model non-blocking transitions with
**cancel-on-exit** actions.

## Consequences

- A visual layer may come later purely as visualization / low-code sugar and
  may look different — it must never become a second source of truth.
- Program structure is inspectable as data (graph export) without executing
  the program.

## Validate new plans against

Any plan that stores editable graph/flow definitions as data (JSON, DB rows)
which then *generate* behaviour is reversing this decision and needs an RFC
that supersedes this ADR.
