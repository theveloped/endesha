# Architecture — as built

This document describes the system as it **is**, verified against source
(baseline: commit `207da0a`, 2026-08-31). Where it disagrees with the
founding design ([design v5](../../automation-framework-design-v5.md)) or an
RFC, this document wins; the *why* behind each load-bearing choice lives in
[docs/decisions](decisions/), and the rules derived from them in
[invariants.md](invariants.md). Known gaps are named honestly in
[§12 Seams](#12-seams--known-gaps).

Sibling guides: [DEVELOPMENT.md](../DEVELOPMENT.md) (running the stack),
[PROGRAMS.md](../PROGRAMS.md) (writing programs).

## 1. What this is

A cell-automation platform: one PC ("host") runs one active **cell** — a set
of logical devices (arm, camera, IO, PLC tags, washer …) declared in a
`cell.yaml` — plus a program runner executing code-first statechart programs
against those devices. Everything communicates over one Zenoh bus
([ADR-0001](decisions/0001-zenoh-bus-is-the-api.md)); every device class is
a contract with interchangeable live/sim/replay providers
([ADR-0004](decisions/0004-contracts-first-class-devices.md),
[ADR-0006](decisions/0006-selectable-sources.md)); the browser is a
first-class bus participant. The platform coordinates automation — it is
**never the safety controller**
([ADR-0011](decisions/0011-safety-out-of-scope.md)).

## 2. Process topology

```
host_api  (FastAPI/uvicorn :8080)          <- the only HTTP surface
+-- config service                          (realm-less; survives cell switches)
+-- supervisor --cell <realized.yaml> --realm cell [--programs <dir>]
    +-- program_runner                      (always-on when programs exist)
    +-- hal:r1    e.g. wf.hal.arm_sim | wf.hal.aubo_i10 | wf.hal.replay.arm
    +-- hal:cam0  e.g. wf.hal.browser_camera | wf.hal.genicam | wf.hal.replay.camera
    +-- hal:plc0  e.g. wf.hal.sim_tags | wf.hal.opcua
```

Independent of that tree: the Zenoh router + WebSocket bridge (Docker,
[deploy/compose.yaml](../deploy/compose.yaml)), the Vite web app, the
recorder (started by `start_stack.ps1`, idle until told to record), and the
optional headless browser camera container.

- **Host API** ([services/host_api](../packages/services/host_api/src/wf/services/host_api/))
  is the machine-level control plane and deliberately tiny: cell registry
  (`GET /cells`), activate/stop (`POST /cells/{id}/activate`, `/cells/stop`),
  health. It never touches Zenoh; nothing else ever gets an HTTP endpoint
  ([ADR-0010](decisions/0010-host-api-scope.md)). **One active cell per
  host**: `SupervisorManager` holds a single supervisor process, tree-kills
  it before activating another cell, and persists the choice to
  `deploy/host.yaml` for restore on boot.
- **Supervisor** ([services/supervisor](../packages/services/supervisor/src/wf/services/supervisor/))
  realizes cell + runtime overlay into concrete providers, spawns them
  (plain `subprocess.Popen`, crash-only), publishes the device inventory,
  cold-switches a single provider on `cmd/set_source`, hosts the cell's one
  `ControlAuthority` (started **before** any provider), and republishes
  children's stdout/stderr + lifecycle events (§9). It deliberately contains
  no task/flow/vision orchestration.
- **Providers (HALs)** serve contracts over the bus. They *check* the
  control lease; only the supervisor's authority grants it.
- **Config service** ([services/config](../packages/services/config/src/wf/services/config/))
  is intentionally outside the supervisor so configuration survives cell
  switches.

## 3. The bus: namespace, key space, interaction shapes

**Namespace.** The operating namespace is a single fixed token: **`cell`**
([core/keys.py](../packages/core/src/wf/core/keys.py)). Whether a device is
served live, simulated, or replayed is **not visible in any key** — that is
what lets one session mix sources per device
([ADR-0002](decisions/0002-realms.md),
[ADR-0006](decisions/0006-selectable-sources.md)). The only second
namespace shape is `replay/<session-id>` for whole-session replay. Two
families are deliberately realm-less so the recorder (which captures
`{realm}/**`) never sees them: `config/**` (persistent, with provenance —
[ADR-0012](decisions/0012-config-service-provenance.md)) and
`recording/**` / `replay/**` transport control.

**Interaction shapes** ([ADR-0013](decisions/0013-reply-envelope.md)):
five, as two primitives plus three codified compositions — **stream**
(pub/sub, latest-wins, no wrapper, `{t, seq}` header), **retained value**
(pub latest-wins + a queryable answering the identical payload; consumed
via the seed-then-subscribe helpers `wf.core.retained` /
`bus.subscribeRetained`, retention classes per
[ADR-0014](decisions/0014-retention-classes.md)), **query/reply**,
**action**, **config**. Every command queryable speaks the **reply
envelope** (`wf.core.envelope` ↔ `web/src/lib/envelope.ts`): request
`{req_id, client_id?, args}` (idempotent resubmission via a
recent-replies ring), reply `{ok, value|goal|error}` with the closed
8-code error enum and per-contract registered reasons; field conventions
in [wire-vocabulary.md](wire-vocabulary.md). Migration is
contract-by-contract (seam #14) — dio, tags, control and washer commands speak it today; the rest
still use their legacy dialects. Long-running operations use the
**action pattern**
([core/action.py](../packages/core/src/wf/core/action.py)): goal queryable →
client-generated UUIDv7 `goal_id`; feedback on `…/{goal_id}/feedback`;
result published *and* queryable (source of truth, `unknown_goal` after a
60 s TTL); one shared `…/cancel` queryable. The action server is strictly
serial: at most one active goal across all actions of a resource; a second
goal is rejected `busy`. Wire format is CBOR throughout
([core/codec.py](../packages/core/src/wf/core/codec.py)); all timestamps are
integer nanoseconds. One deliberate exception to "commands are queryables":
hold-to-jog is a pub/sub *stream* with a watchdog, by design.

**Namespace map.** The docstring of each `keys.py` is the normative key
table; this is the directory:

| Prefix | Contract / owner |
|---|---|
| `{realm}/arm/{rid}/…` | [contracts/arm/keys.py](../packages/contracts/arm/src/wf/contracts/arm/keys.py) — joints/flange/tcp/io/status streams, direct cmds, actions, jog stream |
| `{realm}/camera2d/{cid}/…` | [contracts/camera2d/keys.py](../packages/contracts/camera2d/src/wf/contracts/camera2d/keys.py) — single `image` topic (JPEG payload + CBOR `FrameHeader` attachment), grab/stream cmds, browser-producer election |
| `{realm}/dio/{rid}/…` | [contracts/dio/keys.py](../packages/contracts/dio/src/wf/contracts/dio/keys.py) — `state/channels`, `cmd/set`, `cmd/force` |
| `{realm}/tags/{rid}/…` | [contracts/tags/keys.py](../packages/contracts/tags/src/wf/contracts/tags/keys.py) — PLC/OPC-UA variables: `state/tags`, `cmd/write`, `cmd/force` |
| `{realm}/washer/{rid}/…` | [contracts/washer/keys.py](../packages/contracts/washer/src/wf/contracts/washer/keys.py) — status, door/wash **actions** (cancellable), recipe cmds |
| `{realm}/control/…` | [contracts/control/keys.py](../packages/contracts/control/src/wf/contracts/control/keys.py) — the one cell lease: acquire/release, `state/owner`, authority liveliness |
| `{realm}/program/…`, `{realm}/programs/…` | [contracts/program/keys.py](../packages/contracts/program/src/wf/contracts/program/keys.py) — running unit (singular) vs catalog + file ops (plural) |
| `{realm}/supervisor/{node}/…` | [contracts/supervisor/keys.py](../packages/contracts/supervisor/src/wf/contracts/supervisor/keys.py) — inventory, set_source, logs, events |
| `{realm}/frames/**`, `{realm}/scene/**` | dynamic frame/scene layers, merged with config by [world_model](../packages/world_model/src/wf/world_model/) |
| `{realm}/audit/{service}` | query/reply audit echoes (§9) |
| `config/**` | realm-less persistent config ([services/config/keys.py](../packages/services/config/src/wf/services/config/keys.py)) |
| `recording/**`, `replay/{sid}/**` | recorder control, replay transport ([services/recording/keys.py](../packages/services/recording/src/wf/services/recording/keys.py)) |

Every resource asserts an `…/alive` liveliness token; consumers treat
"authority not alive ⇒ nobody holds the lease" and equivalents as the rule.

## 4. Contracts

A contract package ([ADR-0003](decisions/0003-package-tiers.md),
[ADR-0004](decisions/0004-contracts-first-class-devices.md)) is
`packages/contracts/<name>/` containing `keys.py` (pure key builders; the
docstring is the normative table), `messages.py` (plain dataclasses with
symmetric `to_wire`/`from_wire` — no pydantic, no schema registry), offline
round-trip `tests/`, and — for some — `conformance/`: an installable pytest
suite that exercises **any** implementation purely over the bus (gated on
`WF_CONF_CONNECT`).

Eight contracts exist: `arm`, `camera2d`, `control`, `dio`, `program`,
`supervisor`, `tags`, `washer`. Conformance suites exist for **arm,
camera2d, dio only**; `supervisor` has no `messages.py` at all (ad-hoc
dicts) — see [§12](#12-seams--known-gaps).

**The control lease** ([ADR-0009](decisions/0009-cell-level-lease.md)) is
three cleanly split pieces: `wf.core.lease.ControlLease` (pure, bus-free,
lazy expiry), `ControlAuthority`
([contracts/control/authority.py](../packages/contracts/control/src/wf/contracts/control/authority.py))
— the single grantor, hosted by the supervisor, 30 s TTL, 1 Hz owner
republish — and `LeaseWatcher` (the provider side: subscribes owner +
authority liveliness, seeds with one query so late joiners aren't blind).
Holders renew every 10 s (UI and program runner alike). Programs hold the
lease while running; operators command the *unit*, not the devices, so
PackML commands are deliberately not lease-gated.

## 5. HAL / provider model

The recurring shape is **contract core (shared) + backend ABC
(source-specific) + thin `__main__`**
([ADR-0005](decisions/0005-simulators-are-hals.md)):

| Contract | Shared core | Backends |
|---|---|---|
| arm | [hal/arm_core](../packages/hal/arm_core/src/wf/hal/arm_core/) — lease, jog gating, TCP selection, goal resolution + collision preflight, ruckig trajectories, publishing | `arm_sim`, `aubo_i10`, `replay.arm` |
| camera2d | [hal/camera2d_core](../packages/hal/camera2d_core/) | `genicam`, `browser_camera`, `replay.camera`, external TS headless renderer |
| dio / tags | [hal/channels_core](../packages/hal/channels_core/) + a per-contract schema | `sim_dio`, `sim_tags`, `opcua`, arm-onboard facade |
| washer | [hal/ecoclean](../packages/hal/ecoclean/) `WasherCore` | `ecoclean_sim`, `ecoclean` (live OPC-UA) |

Call direction is inverted on purpose: the backend owns its state threads
and pushes into the core (`publish_motion`/`publish_io`); the core calls
back for `run_path`/`set_do`/`stop`.

**One process, several devices.** A resource may `provide` devices of
another contract in-process (`provides:` in cell.yaml; providable: `dio`,
`tags`). The arm hosts its onboard IO as a real `dio` device sharing the
arm's lease watcher — no bus hop; the Ecoclean washer conversely provides
its raw PLC as a visible, forceable `tags` device. Provided devices appear
in the inventory but have no sources of their own (`set_source` →
`provided_by:<host>`).

**Selection pipeline** ([ADR-0006](decisions/0006-selectable-sources.md)):
`cell.yaml` declares per-resource `sources: {live|sim|browser_sim|replay:
{kind, params, launch}}`; a runtime overlay picks `active_sources: {rid:
mode|off}`; `realize_cell` collapses both into concrete providers (an `off`
resource is omitted), writes the result to a tempfile, and children only
ever see that realized file. Spawn mapping lives in
[supervisor/procs.py](../packages/services/supervisor/src/wf/services/supervisor/procs.py)
(`PROVIDER_MODULES`); `launch: external` lists the device in inventory
without spawning (used by the headless camera container). Source switching
is a cold restart of that one provider, not of the tree.

## 6. Program layer

([ADR-0007](decisions/0007-code-first-programs.md),
[ADR-0008](decisions/0008-packml-in-runner.md); authoring guide:
[PROGRAMS.md](../PROGRAMS.md).)

A program is a `python-statemachine` StateChart subclass
([program/program.py](../packages/program/src/wf/program/program.py)) with
`roles` (role → contract, bound to devices at load; unbound roles default to
the sole device of that contract), `params`, declarative `triggers`
(`on_channel` edges, `after` dwell timers), and an `hmi` map that renders
waiting events as operator buttons. State actions (`run_<state>`) run on
their own threads and are **cancelled on state exit** — Hold/Stop/Abort
included. The graph the UI shows is derived from the class
([program/graph.py](../packages/program/src/wf/program/graph.py)); code is
the only source of truth.

The runner ([services/program_runner](../packages/services/program_runner/src/wf/services/program_runner/))
hosts the **PackML unit machine** (`unit.py`, 17 states, pure — no bus, no
threads) and owns all threading: a single driver thread touches the
machines; action threads are cancelled/joined (3 s, else abort
`action_hang`); the lease renews every 10 s (loss ⇒ abort); `program/state`
ticks at 1 Hz. The runner acquires the lease on start, stops bound arms on
Stop/Abort, and latches a safety abort on any bound arm's
`estop`/`protective_stop`. Programs reach devices only through proxies
([program/proxies.py](../packages/program/src/wf/program/proxies.py)) —
blocking calls consult the action's context so cancel propagates into
in-flight goals. Discovery re-imports fresh modules per scan; a broken file
is listed with its error, never crashing the runner. The editor path
(`source`/`save`/`delete`) writes atomically and re-scans.

Real examples: [deploy/programs/](../deploy/programs/) (`demo_pick.py` is
canonical),
[deploy/ecoclean/programs/ecoclean_cycle.py](../deploy/ecoclean/programs/ecoclean_cycle.py)
(operator-paced HMI pattern).

## 7. world_model

[packages/world_model](../packages/world_model/src/wf/world_model/) is the
shared kinematics/geometry/frames library (URDF FK, damped-least-squares
IK — own IK by decision, the vendor SDK's is never used —, loose-goal
sampling, Pinocchio+Coal collision, ruckig + cartesian trajectories, jog,
live frame/scene overlays). It is a library, not a service: its production
consumers are `ArmCore` (goal acceptance, preflight, trajectories, jog) and
the `wfctl` scene importer. The web app deliberately reimplements FK/frame
math in TypeScript for the twin (§10), so world_model is not the viewport's
source of truth.

## 8. Config & persistence

([ADR-0012](decisions/0012-config-service-provenance.md).) The store
([services/config/store.py](../packages/services/config/src/wf/services/config/store.py))
is pure (no zenoh): atomic `store.yaml` writes + append-only
`history.jsonl` provenance. The service serves glob queryables for reads,
`cmd/set`/`cmd/delete` for writes, and republishes the normalized value on
the written key so live subscribers see edits (tombstone = empty payload).
Two normalizations are applied centrally so every writer gets the same
semantics: **frames** keep `nominal` vs `calibration` separated (a manual
write drops stale calibration; a calibration write preserves nominal), and
**intrinsics** are normalized to the ROS `CameraInfo` layout. Key shapes
are regex-validated; errors are machine-readable (`invalid_key:`,
`cycle:`, `reserved_name:flange`, …). Program-scoped poses
(`config/programs/<name>/poses/…`) resolve before global poses.

## 9. Observability

Three mechanisms, all ordinary realm topics — so recordings capture them
and replay debugging includes them for free:

- **Service logs** — the supervisor pipes every child's stdout/stderr,
  mirrors lines to its own stderr, parses the level, and republishes on
  `{realm}/supervisor/{node}/log/<service>` with a 300-line ring served on
  query ([supervisor/telemetry.py](../packages/services/supervisor/src/wf/services/supervisor/telemetry.py)).
- **Supervisor events** — `service_started/stopped/exited`, `spawn_failed`,
  `source_switched`, … on `…/events`, 200-entry ring.
- **Query/reply audit** ([core/audit.py](../packages/core/src/wf/core/audit.py)) —
  zenoh queries are point-to-point and invisible to passive subscribers, so
  every *mutating* queryable handler is wrapped in `QueryAudit`, which
  echoes `{key, params, request, reply, ok, duration_ms}` (values bounded
  at 2 KB) onto `{realm}/audit/<service>`, with a 200-record history ring
  behind the same key. Policy: **reads and state polls are not audited.**
  Instrumented: control acquire/release, supervisor set_source, config
  set/delete, all program commands, arm direct commands + action
  submissions, dio/tags set/write/force.

Base logging is deliberately boring stdlib-to-stderr
([core/log.py](../packages/core/src/wf/core/log.py)); the structure on the
bus comes from the supervisor re-parsing that format — the named seam if
structured logging is ever wanted.

## 10. Web app

[web/](../web/) — React 19 + Vite + TypeScript, no router library (hash
router in `src/shell/router.ts`; the URL carries realm + tool), no store
library (one `RuntimeProvider` context). Two build entries: the operator UI
and a headless render-only camera bundle driven by Puppeteer in Docker.

- **Bus citizenship**: the browser speaks real zenoh over the WebSocket
  bridge (`@eclipse-zenoh/zenoh-ts`, pinned 1.9.0; gate evidence in
  [web/SPIKE.md](../web/SPIKE.md)). `src/lib/bus.ts` is the only wrapper:
  latest-wins ring subscriptions, query/queryAll, and *server-side*
  primitives — the browser also **serves** contracts: the headless page
  implements the full camera2d provider in TS, and the in-tab browser
  camera producer holds a fenced producer lease and answers per-client
  render queries.
- **Contract mirroring is explicit**: `src/lib/config.ts` mirrors every
  Python `keys.py`; `codec.ts` ↔ `wf.core.codec`; `actions.ts` ↔
  `wf.core.action` (feedback/result subscribed *before* the goal query);
  `framemath.ts`/`geometry.ts` ↔ `wf.core.frametree`/`frames`. Two CBOR
  codecs on purpose: `cbor-x` for reads; a hand-rolled write-side encoder
  for camera2d because `cbor-x` encodes `1.0` as an int and the Python
  contract declares floats. Cross-language fidelity is guarded by the CBOR
  gate scripts (`web/scripts/_cbor_gate_*`), currently run manually.
- **Rendering**: one r3f canvas; URDF twin driven by refs written at bus
  rate and read per-frame (200 Hz data decoupled from render rate); Z-up
  world inside a Y-up three scene; TCP drag gizmo commits `execute_path`
  goals; the sim camera renders the same twin from calibrated intrinsics so
  camera image and viewport match by construction.
- **Conventions that carry weight**: no optimistic updates (controls render
  the state stream, never the click); every command control carries
  `className="cmd"` and `[data-realm="replay"] .cmd` flattens all commands
  in replay automatically; stale-realm samples are rejected by tagging
  every sample with its session+prefix; PackML button enablement comes from
  a client-side transition table (`src/lib/unit.ts`).
- Pages: Overview (twin + panels), Operate (hold-to-jog), Programs +
  Program Studio (catalog, PackML bar, derived graph with live overlay,
  CodeMirror editor), IO, Cameras, Frames/Configure, Topics, Logs, Queries
  (audit tail), HMI (operator page), replay routes under `#/replay/<sid>/…`.

## 11. Deploy model

[deploy/](../deploy/) is the host's content: `cell.yaml` (the default
dev-cell: `r1` aubo/sim/replay arm providing onboard IO as `io0`, `cam0`
eye-in-hand camera with four sources, `plc0` sim tags), `runtime/*.yaml`
overlays (`default` = fully self-contained, `sim`, `dev` = live hardware,
`commissioning`, `replay-debug`), sibling `programs/`, the config store
under `config/`, and one directory per additional cell
([deploy/ecoclean/](../deploy/ecoclean/) — the washer cell that replaced
the old ecoclean-controller repo). Zenoh configs under
[deploy/zenoh/](../deploy/zenoh/) encode a real constraint: host-side
processes run in **client** mode so they never gossip a locator the Docker
bridge can't reach. Validation is front-loaded: dio/tags channel schemas
are checked when the cell loads, "so a typo fails the cell, not a run".

## 12. Seams — known gaps

Named deliberately: an as-built doc that admits what is unfinished is one
you can trust. Each entry is either *accepted* (fine as-is for now) or
*wants fixing*. Review this list when planning — a plan that touches a seam
should either close it or consciously leave it.

| # | Seam | Status |
|---|---|---|
| 1 | `POST /cells/<id>/activate` without a runtime falls back to `sorted(runtimes)[0]` — for the ecoclean cell that is **`live`** (the real OPC-UA washer). | **wants fixing** (add `default.yaml` or refuse to default to live) |
| 2 | The shipped host-API path starts the config service without `--realm`, so `cell/audit/config` is **never published** despite the Queries page expecting it. | **wants fixing** |
| 3 | Conformance suites exist only for arm / camera2d / dio; control, program, tags, washer have none; `supervisor` has no `messages.py` (inline dicts). | wants fixing, incremental |
| 4 | No camera2d program proxy — programs cannot grab images yet. | accepted until the vision RFC lands |
| 5 | Stale `"live"` realm defaults linger in the two conformance conftests and the recorder (`start_stack.ps1` overrides); `wfctl` docstring says live, code says cell. | wants fixing, trivial |
| 6 | Action-server driver-restart semantics (design v5 App. A `aborted {cause: driver_restart}`) are an explicit phase-1 no-op — no goal persistence. | accepted |
| 7 | The replayer has no launcher: whole-session replay is a manual `python -m wf.services.recording.replayer <file>`. | accepted |
| 8 | `frames_live` has no time-aware buffer ("every consumer resolves at 'now'"); `FrameLowConfidence` etc. are stubs. | accepted until vision RFC |
| 9 | `supervisor --with-config` exists but the host API never passes it (config is host-API-owned in the shipped path). | accepted (or delete the flag) |
| 10 | `sim_dio` / `opcua` are registered providers no shipped cell selects; `plc0` has no `live` source. | accepted |
| 11 | `web/tests/` is empty; the CBOR wire gate and lint/tsc are the only web verification, and the gate is not in CI (no CI exists yet). | wants fixing eventually |
| 12 | Web fallback constants when no host API answers: `CELL_NAME="dev-cell"`, `RID="r1"`, `CID="cam0"`. | accepted |
| 13 | Orphaned `deploy/programs/__pycache__/ui_made_532*.pyc` from a deleted UI-authored program. | trivial cleanup |
| 14 | Envelope migration ([ADR-0013](decisions/0013-reply-envelope.md)) in progress: **dio + tags** (shared `ChannelsCore`), **control**, and **washer** (commands; its door/wash actions await the arm/action step) speak it, with conformance enforcement on dio and control; `program`, `camera2d`, `arm`, `config` still reply legacy dialects (their audit records show `ok: null` until migrated — no sniffing, no backcompat). | in progress, per RFC §9 |

## 13. Keeping this document honest

Maintained under the lifecycle in [docs/README.md](README.md): the PR that
changes the architecture updates this file and adds ADRs; seams move rows
(or vanish) when closed; a periodic drift audit re-verifies this document
against source. Baseline of last full verification: `207da0a` (2026-08-31).
