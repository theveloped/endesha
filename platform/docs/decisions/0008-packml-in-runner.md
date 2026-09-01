# ADR-0008 — PackML unit states live in the runner, never in user programs

Date: 2026-08-15 (program-layer RFC §0, §3.4) · Status: accepted, implemented

## Decision

Operator-facing control follows PackML vocabulary (Start / Hold / Stop /
Abort / Reset …), implemented once as the unit machine inside the program
runner. User programs express only their own application states; they are
hosted inside the unit machine and interrupted by it.

`hold` re-runs the interrupted state's entry action from the top (v1);
resumable actions are a later increment.

## Consequences

- Every program gets the same operator semantics and HMI buttons for free.
- Programs cannot redefine or bypass Stop/Abort behaviour.

## Validate new plans against

Does the plan put lifecycle/abort/hold logic inside a user program or a
device HAL? That logic belongs to the runner's unit machine.
