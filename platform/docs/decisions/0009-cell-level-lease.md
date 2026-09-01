# ADR-0009 — One cell-level control lease; input forcing is ungated

Date: 2026-08-15 (program-layer RFC §2.4, review decisions 1 & 4) · Status: accepted, implemented

## Decision

Mutating authority is a **single cell-level lease** with one holder for all
devices — not per-device leases. Forcing an OUTPUT is lease-gated (it drives
an actuator). Forcing an INPUT is ungated: a visibly flagged
test/commissioning override that must keep working while a program holds the
lease (e.g. feeding parts to a running program in sim).

## Consequences

- No split-brain cells where the UI drives one device while a program drives
  another.
- Commissioning and testing stay possible without stopping the program.

## Validate new plans against

- Does a new mutating surface (new contract command, new UI control) check
  the lease? (Reads and input-forces don't.)
- Does the plan introduce per-device or per-subsystem authority? That
  contradicts this ADR.
