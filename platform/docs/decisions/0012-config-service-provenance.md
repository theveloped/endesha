# ADR-0012 — Config is realm-less, goes through the config service, keeps provenance

Date: 2026-06 (design v5 §4.4), sharpened 2026-08 · Status: accepted, implemented

## Decision

Persistent configuration (TCPs, calibrations, frames, camera intrinsics,
scene, recipes) is realm-less, addressed by key, and mutated only through
the config service, which persists to the store (`deploy/config/store.yaml`)
and appends provenance to a history log (`deploy/config/history.jsonl`).

## Consequences

- Sim and live share one config truth; a calibration done against sim data
  is the same kind of object as one done live.
- "Who changed this TCP and when" is answerable from the history log.

## Validate new plans against

New persistent state must choose explicitly: realm-scoped (recorded,
ADR-0002) or config (provenance, this ADR). Files on disk that services
read directly are neither and need justification (assets like URDF/meshes
are the accepted exception, addressed *by* config keys).
