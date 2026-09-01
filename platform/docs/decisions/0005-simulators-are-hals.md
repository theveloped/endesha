# ADR-0005 — Simulators are HALs; swappability is tested, not hoped for

Date: 2026-06 (design v5 §2.1 L2) · Status: accepted, implemented

## Decision

A simulator implements the same contract as the real hardware
(`arm_sim` ↔ `aubo_i10`, `sim_dio`, `sim_tags`, the Ecoclean washer sim).
The conformance suite runs against sim HALs in CI and on demand against real
hardware. There is no "mock mode" flag inside drivers.

## Consequences

- Any program is simulatable end to end, because every contract has a sim
  provider (this is a *requirement* on new contracts, ADR-0004).
- Sim fidelity work (motion profiles, IO timing) happens inside the sim HAL,
  invisible to everything upstream.

## Validate new plans against

A plan that adds a device/capability but defers its sim provider breaks the
"any program is simulatable" property — the sim provider is part of the
feature, not a follow-up.
