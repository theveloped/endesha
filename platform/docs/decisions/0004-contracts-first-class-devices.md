# ADR-0004 — Every device class is a first-class contract; the arm is a peer

Date: 2026-08-15 (program-layer RFC §0, §2) · Status: accepted, implemented

## Decision

All device types are first-class contracts with named channels: `arm`,
`camera2d`, `dio`, `tags` (OPC-UA/PLC variables), `washer`, with `serial` /
`http` to follow the same pattern. The arm is a peer, not the centre — a cell
with no arm (e.g. two serial testers) must work.

A contract package contains exactly: the key-space template, message schemas,
action semantics, required config keys, and a **conformance test suite** that
exercises any implementation purely over the bus.

The arm's onboard IO is exposed **as a `dio` device** (facade), so programs
and panels have one IO API regardless of where the pins physically live.

## Consequences

- Adding a device class = new contract + HAL + panel plugin; core, recorder,
  replayer, supervisor untouched.
- UI panels key off contract types and descriptors, never off specific
  hardware.

## Validate new plans against

- Does the plan special-case the arm (or any single device) where the
  contract abstraction should carry it?
- Does a new external interaction (sensor, PLC, HTTP box) get a contract with
  named channels and a sim provider — or is it a one-off client hidden inside
  a program or service?
