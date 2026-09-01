# WF automation platform

Zenoh-based cell automation: contracts per device class, swappable
live/sim/replay providers, code-first statechart programs, web operator UI.

## Read before designing anything

- `docs/README.md` — the doc map: the single entry point to all
  documentation and the complete inventory of agent context. Every markdown
  doc in the repo must be reachable from it (`pixi run docs-check`
  enforces this); never add guidance anywhere it can't be found from there.
- `docs/architecture.md` — the as-built system, incl. the seams list.
  Trust it over the RFCs and over `../automation-framework-design-v5.md`.
- `docs/invariants.md` — hard rules. **Every plan, RFC, or non-trivial
  change is checked against this list before implementation**; if a plan
  strains against a rule, say so explicitly and propose superseding the
  ADR rather than working around it.
- `docs/decisions/` — why things are the way they are (ADRs).
- `PROGRAMS.md` — how automation programs are written; `DEVELOPMENT.md` —
  how to run the stack.

## When you change the architecture

The PR that lands an architectural change also updates
`docs/architecture.md` (including seam rows it opens or closes), adds an
ADR to `docs/decisions/` for each durable decision (and a row in the
`docs/README.md` index), and — rarely — a rule to `docs/invariants.md`.
Docs land with the change, not after. RFCs live at the repo root while in
flight and become historical once landed. Durable project knowledge goes in
this docs tree, never only into agent memory.

## Layout

- `packages/core` — zenoh session, CBOR codec, action pattern, frames,
  lease, log, audit. `packages/contracts/*` — per-device-class keys +
  messages + conformance tests, no implementation. `packages/hal/*` —
  implementations incl. simulators. `packages/services/*` — supervisor,
  config, recording, host_api, program_runner. `packages/program` — the
  `wf.program` SDK. `packages/world_model` — kinematics/collision.
- Dependency direction: core → contracts → hal → services/program. Never
  import against the arrow; HALs never import HALs.
- `web/` — React + Vite operator UI. `deploy/` — cell.yaml, host.yaml,
  compose, config store, programs.

## Checks before committing

```powershell
pixi run python -m pytest
pixi run docs-check
cd web; npx tsc -b; npm run build; cd ..   # build also syncs static assets
docker compose -f deploy/compose.yaml config --quiet
```

Python is run through pixi (`pixi run python ...`); packages are editable
installs, no reinstall needed after edits. Tests live next to each package
(`packages/*/tests`); new contract implementations must pass the contract's
conformance suite.
