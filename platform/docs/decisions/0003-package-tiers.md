# ADR-0003 — Package tiers with one dependency direction

Date: 2026-06 (design v5 §2.1, §8.1) · Status: accepted, implemented

## Decision

The workspace is layered; lower layers know nothing about upper ones:

    core  →  contracts/*  →  hal/*  →  services/*, program
    (transport & patterns) (device classes) (implementations) (orchestration)

- `wf.core`: Zenoh session, CBOR codec, action pattern, frames, lease, log,
  audit. Knows nothing about robots or cameras.
- `wf.contracts.*`: one package per device class — keys, message schemas,
  semantics, conformance tests. No implementation.
- `wf.hal.*`: bind a contract to concrete hardware or to a simulator.
- `wf.services.*` / `wf.program`: supervisor, config, recording, host API,
  program runner/SDK — orchestrate via contracts, never via HAL imports.

## Consequences

- A HAL never imports another HAL; shared behaviour is hoisted to a
  `*_core` HAL package (`arm_core`, `dio_core`, `channels_core`) or to the
  contract.
- `world_model` is a peer library used by services and HALs (kinematics,
  collision); it depends on `core` only.

## Validate new plans against

Draw the imports the plan adds. Any arrow pointing right-to-left in the
diagram above (e.g. a contract importing a HAL, core importing anything)
means the plan is placing logic at the wrong tier.
