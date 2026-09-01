# ADR-0006 — Logical devices with selectable sources (live/sim/replay/off)

Date: 2026-08 (selectable-source refactor, pre-program-layer) · Status: accepted, implemented

## Decision

`cell.yaml` declares *logical* devices; a runtime overlay selects each
device's **source**: `live`, `sim`, `replay`, or `off` — per device, not
globally. The supervisor is a provider orchestrator: one provider process per
resource, a process may `provide` several contracts, `launch: module |
external`, crash-only restart, device inventory published for the UI and the
program runner.

## Consequences

- Namespace and source are decoupled: a program binds roles to logical
  devices and runs unchanged when a device flips live↔sim↔replay.
- Mixed cells (live arm + simulated IO + replayed camera) are a supported,
  ordinary configuration, not a hack.

## Validate new plans against

Does the plan assume a whole-cell mode ("the cell is in sim") anywhere?
Per-device source selection is the model; whole-cell switches are sugar.
