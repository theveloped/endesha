# ADR-0010 — Host API = cell registry + supervisor lifecycle, nothing else

Date: 2026-08-18 · Status: accepted, implemented

## Decision

A small FastAPI host API exists for exactly what the bus cannot do: managing
the lifecycle of the bus's own participants. It owns the cell registry and
starting/stopping the active cell's supervisor — **one active cell per
host**. Device commands, program control, config — everything else — stays
on Zenoh (ADR-0001).

## Consequences

- The navbar switches cells through the host API; after that the UI is a
  pure bus citizen again.
- The host API must never accrete device endpoints "because HTTP was
  convenient".

## Validate new plans against

Any new host API endpoint needs the same justification this ADR had: is this
about processes that must exist *before* the bus does? Otherwise it's a
queryable.
