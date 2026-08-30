# RFC — Agentic cell commissioning and continuous stewardship

Status: **draft for review** (2026-08-30). Branch: `claude/agentic-cell-setup-monitor-c5ubfs`.
Builds on the completed program layer (`program-layer-rfc.md` steps 0–7) and the
observability slice (`92631f2`).

Goal of this document: get from "a platform an engineer drives" to "a platform an
**agent** can commission and steward", where

1. an engineer installs hardware and this stack on a machine that reaches it,
   hands the agent a **requirements document**, and the agent brings the cell up —
   asking the engineer only what it genuinely cannot determine itself;
2. the agent then **watches the cell forever**: it triages every fault, fixes what
   is a cell-level problem, files a GitHub issue when the problem is platform-level,
   and continuously **hill-climbs** the parts that can be better (vision accuracy,
   pick/place robustness, cycle time).

Part I and II are a review of what exists. Part III is the target design. Part IV
is the delivery order. Nothing in Part III/IV is implemented yet.

---

## Part I — What exists today

### 1. Programs

A program is a Python file under `deploy/programs/` defining one
`wf.program.Program` subclass — a [python-statemachine](https://python-statemachine.readthedocs.io/)
`StateChart`. `platform/PROGRAMS.md` is the authoring reference; the code is
`platform/packages/program/src/wf/program/`.

| Piece | Where | What it does |
|---|---|---|
| `Program` | `program/program.py` | `StateChart` base. Class attrs `program_name`, `roles`, `params`, `triggers`, `hmi`. `describe()` exports doc/states/events/graph for the catalog. |
| `Machine` / `Roles` | `program/machine.py` | Device facade. `roles = {"arm": "arm"}` (role → contract) is resolved to device ids at Load; `self.m.arm` is the proxy. Reserved helper names (`pose`, `device`, `ids`, `rid`, `bindings`, `machine`) are rejected as role names. |
| Proxies | `program/proxies.py` | `ArmProxy`, `DioProxy`/`TagsProxy` (`channels_core`-shaped), `WasherProxy`. Blocking calls that raise `ActionCancelled` on cancel. |
| `ActionContext` | `program/context.py` | The cancel token every action runs under; thread-local so proxies find it without user code passing it. `check()`, `sleep()`, `on_cancel()`. |
| Triggers | `program/triggers.py` | `on_channel(role, channel, edge=..., event=...)` and `after(seconds, state=..., event=...)`. Evaluated by the runner, not by user code. |
| Graph | `program/graph.py` | States/transitions/guards/triggers **plus source anchors** (file + line of each `State(...)`, `a.to(b)`, `run_*`, guard). Drawn with React Flow; click-through to source. |
| Runner | `services/program_runner/` | Owns the PackML unit machine (`unit.py`), the driver thread, action threads, the control lease, and the bus. Discovers programs from a directory; `save`/`source`/`delete` over the bus back the in-browser editor. |

The load-bearing ideas:

- **The program never sees the platform.** No bus, no threads, no lease, no PackML
  in user code. It sees `self.m` (roles), `self.p` (params), `emit()`, `log()`.
- **Contracts are interfaces, roles are constructor arguments, `cell.yaml` is the
  container config.** A program that says `roles = {"arm": "arm", "io": "dio"}` runs
  on any cell that has one of each — this is the reuse mechanism (design v5 §8.2).
- **One program, three backends.** `live` / `sim` / `replay` is a *runtime overlay*
  choice per device (`deploy/runtime/*.yaml`), never a program concern. The existing
  `commissioning.yaml` overlay already mixes them (`r1: sim`, `cam0: live`) — that
  mixed mode turns out to be the backbone of safe bring-up (§III.3).
- **Non-blocking transitions with cancel-on-exit** (Vention model): an event is
  handled immediately, the running action is cancelled, in-flight arm goals are
  cancelled through `ctx.on_cancel`. Hold re-runs the state's action from the top;
  resumable actions are explicitly deferred.
- **PackML vocabulary is the operator contract** and is on the bus, so an HMI, a
  CLI and an agent all drive the same nine commands.
- **Everything a program does lands under `{realm}/**`**, so the recorder captures
  it and replay reconstructs the timeline for free.

Failure modes are already named strings, which matters for triage: `action_error:<state>:<msg>`,
`action_crash:<state>:<repr>`, `motion_rejected:<reason>` (incl. `collision:{a}|{b}`,
`target_outside_limits`), `safety:*`, `lease_lost:*`, `washer_fault:<rid>:<code>`,
and Load-time `unknown_program`, `program_broken:<import error>`, `unknown_params:x`,
`bind:<role>:...`.

### 2. Everything that can be recorded

The recorder (`services/recording/recorder.py`) subscribes **`{realm}/**`** and
writes MCAP: one channel per zenoh key, `message_encoding="cbor"`, message data =
CBOR `[payload, attachment]` with the payload bytes **verbatim**. Its own control
plane is realm-less (`recording/cmd/*`) so it never records itself. `McapSource`
reads it back; the replayer republishes into `replay/{session_id}/**`.

So "what is recordable" is exactly "what is published under the realm prefix":

| Stream | Key | Content |
|---|---|---|
| Arm | `{realm}/arm/{rid}/state/{joints,status,flange,tcp,io}` | joints, mode/safety, flange & TCP pose, onboard IO |
| Arm goals | `{realm}/arm/{rid}/action/execute_path/{goal_id}/{feedback,result,snapshot}` | progress, terminal result, and the **execution snapshot** (resolved waypoints in base, active TCP, speed scale, driver version, frame resolution) |
| dio / tags | `{realm}/{dio,tags}/{rid}/state/{channels,tags}` | on change + 1 Hz keepalive |
| Washer | `{realm}/washer/{rid}/state/status` | phase, door, fault code, program, sequence |
| Camera | `{realm}/camera2d/{cid}/image` (+ `state/status`) | frame bytes with a header attachment |
| Program | `{realm}/program/{state,log,transitions}`, `{realm}/programs/catalog` | unit + program state incl. `waiting_for`, `self.log()` + runner notes, every transition |
| Supervisor | `{realm}/supervisor/{node}/{devices,descriptor}` | device inventory and active sources, process state |
| **Service logs** | `{realm}/supervisor/{node}/log/{service}` | **every captured stdout/stderr line** of every supervised child: `{t, level, stream, source, message}`, level parsed best-effort, 300-line ring buffer behind a queryable for late joiners (`telemetry.LogHub`) |
| **Lifecycle events** | `{realm}/supervisor/{node}/events` | `started` / `stopped` / `exited` (with exit code) / `spawn_failed` / `source_switched`, 200-deep ring + queryable (`telemetry.EventLog`) |
| **Query/reply audit** | `{realm}/audit/{service}` | **every handled command**, echoed as an ordinary sample: `{t, service, key, params, request, reply, ok, error, duration_ms}` (`core/audit.py`). Values >2 KB truncated; audit failures never disturb the handler; the echo is observability only, so replay never re-executes a command. |

`QueryAudit` is adopted today in: supervisor (`set_source`), config (`set`/`delete`),
program runner (all commands), control authority (`acquire`/`release`),
`channels_core` (`set`/`force`/`write` for both dio and tags), and the arm's
`ActionServer` (goal submit and cancel; result polls are deliberately not echoed).

Two surfaces render this: `#/cell/logs` (merged service+event tail, source rail,
level filter, ring-buffer late join) and `#/cell/queries` (live audit stream with
request/reply detail). `#/cell/topics` is a generic bus inspector.

**Not recorded, deliberately or by omission:**

- **The config store.** `config/**` is realm-less by design (shared across realms),
  so pose/frame/TCP/intrinsics *values* never enter the MCAP. The *write commands*
  do, via `{realm}/audit/config`. The store keeps its own append-only
  `deploy/config/history.jsonl` (`{t, key, old, new, revision}`).
- **Non-PUT samples.** The recorder counts and drops DELETEs.
- **Only the first reply** of a multi-reply query is captured by `QueryAudit`.
- **camera2d, washer and recorder commands** are not wrapped in `QueryAudit` —
  `cmd/grab`, `cmd/configure`, `cmd/stream_*`, `cmd/get_recipe`, `cmd/set_recipe`,
  `cmd/stop_door` and `recording/cmd/*` leave no trace, and the washer's own
  `ActionServer` is constructed without an audit (`hal/ecoclean/core.py:103`), so
  `open_door` / `start_wash` / `reset` are unaudited too.
- **Host API HTTP calls** (`/cells`, `/activate`, `/stop`) are outside the bus.
- **The cell event log `{realm}/events`** from design v5 §4.6 does not exist.
  `core` has no `emit_event()`. The supervisor's `events` topic is the only
  event stream and it is scoped to process lifecycle.

---

## Part II — Gap analysis against the goal

Ordered by how hard they block the two loops.

### A. The cell is not legible to a headless agent

1. **No cell event log.** There is no single "what happened" stream. An agent has
   to join five topics and infer semantics. Design v5 §4.6 already specifies it.
2. **No CLI for the observability that exists.** `wfctl` has 40 subcommands and
   none of them are `logs`, `events`, `queries`/`audit`, `topics` or `health`. The
   Logs and Queries pages are browser-only. An agent on the commissioning box has
   no way to tail a crashing HAL's traceback.
3. **No recording analysis tool.** `McapSource` exists; nothing built on it. Asking
   "what happened in the 30 s before that abort" means writing a bespoke reader
   every time. There is no `timeline`, `slice`, `grep` or `stats` over a recording.
4. **Recording is manual and unbounded.** `cmd/start`/`cmd/stop` or `--autostart`.
   There is no rolling ring with an incident snapshot on abort — which is precisely
   the shape an incident-driven agent needs.
5. **No health summary.** Liveliness tokens, supervisor descriptor, unit state and
   lease owner are four separate lookups.

### B. Commissioning has no machinery

6. **No hardware discovery.** Nothing scans a subnet for an Aubo controller,
   enumerates GenICam devices through a CTI, browses an OPC-UA namespace into a
   `tags:` inventory, or lists serial ports. The OPC-UA HAL can browse but only
   from inside a running provider. Without this the agent cannot fill in `cell.yaml`
   and must interrogate the human for every field.
7. **No `cell.yaml` schema or validator.** Errors surface when the supervisor fails
   to spawn a provider. There is no `wfctl cell validate` / `doctor`.
8. **No calibration service.** Design v5 §5.5 is unimplemented: no intrinsics
   capture, no hand-eye, no touch-off action. `config/intrinsics/{cid}` and
   `config/arm/{rid}/tcp/{name}` are writable but nothing produces the values.
   For a vision-guided cell this is the single largest commissioning gap.
9. **Windows-only launcher.** `start_stack.ps1` / `stop_stack.ps1` are PowerShell.
   A box that sits next to the hardware is usually Linux; only the Docker compose
   path works there today.
10. **No cell-type / skills tiers.** Design v5 §8 describes `fleet/cell-types/*`
    and `platform/packages/skills/*`; neither exists. Every new cell starts from a
    hand-written `cell.yaml` and hand-written programs.

### C. There is no vision layer at all

11. **`{realm}/vision/{pipeline}/{result,overlay}` does not exist.** Cameras
    publish images; nothing consumes them. There is no vision contract, no pipeline
    runtime, no pipeline discovery, no `VisionProxy`, no overlay renderer.
12. **No dynamic frames.** `{realm}/frames/{name}` (design v5 §4.5: pose + source +
    confidence + TTL, merged into the live tree, time-buffered so an image at
    `t_capture` combines with the flange pose *at `t_capture`*) does not exist.
    `frames_live.py` builds the tree from static config plus kinematics only. So
    "move to what the camera just found" is not expressible.
13. **No replay regression harness.** Design v5 §8.4 names replaying a site's
    recordings through a new pipeline as *the* upgrade gate. Nothing implements it —
    and it is also exactly the scorer a hill-climbing loop needs.

### D. There is nothing to hill-climb *with*

14. **No metrics.** Cycle time, per-state dwell, per-move duration, retry counts,
    abort rates, collision rejections, vision latency/confidence are all derivable
    from `program/transitions` + action results + the audit stream, but nothing
    derives them. There is no scoreboard, so "better" is not measurable.
15. **No declared tuning surface.** Program `params` and `cell.yaml` `config:`
    blocks are untyped and unbounded. Nothing says which knobs an optimizer may
    touch or within what range — an agent asked to make the cell faster has no way
    to know that `ruckig_defaults.vmax` is dangerous and `settle_s` is not.
16. **Per-move speed is not wired.** `Waypoint.speed` / `.accel` are "accepted and
    recorded but currently unused"; only cell-level `ruckig_defaults` apply. Speed
    tuning currently cannot even be *expressed* per move.
17. **No experiment protocol.** No baseline/variant runs, no comparison, no
    auto-revert, no promotion path.

### E. The agent itself has no home

18. **No `.claude/` directory, no `CLAUDE.md`, no skills, no CI.** Nothing tells an
    agent how to run the stack, what the checks are, or what it must not touch.
    `.github/workflows` does not exist, so nothing gates a change today.
19. **No capability boundary.** `wfctl` will happily jog a live robot. There is no
    read-only / sim-write / live-write distinction an autonomous loop can be pinned to.
20. **No defined path from a cell fault to a platform issue.** (The mechanism —
    GitHub — is available; the *policy and evidence bundle* are not defined.)

---

## Part III — Target design

### 1. Two loops, one repository layout

```
fleet/deployments/<site>/
├─ requirements.md          # the human input; the agent's brief
├─ cell.yaml                # bindings: serials, IPs, mounts, channels, tags
├─ runtime/{sim,live,bringup-*}.yaml
├─ frames/ scene/           # CAD-derived site geometry
├─ programs/ pipelines/     # site programs and vision pipelines
├─ tuning.yaml              # declared knobs + bounds + risk class  (§III.6)
├─ acceptance.yaml          # criteria derived from requirements.md (§III.4)
├─ snapshots/               # exported operational state (calibrations, poses)
└─ journal/                 # commissioning + steward reports, incident bundles
```

`fleet/` is new; `platform/` stays the semver'd product. The dependency rule from
design v5 §8.1 holds: deployments → cell types → skills → contracts.

### 2. Loop A — the commissioning agent

Input: `requirements.md`. Output: a cell that passes `acceptance.yaml`, plus a
commissioning report in `journal/`.

**Phase 0 — Intake.** Parse the requirements into a *cell brief*: required roles
and contracts, part/fixture geometry, throughput and takt targets, safety
constraints, acceptance criteria, and an explicit **unknowns list**. The agent then
asks the engineer *one structured questionnaire* generated from the unknowns —
not a free-form conversation. Every answer is written back into `requirements.md`
so the brief stays the single source of truth and the next run does not re-ask.

**Phase 1 — Discover.** `wfctl probe` against the machine's networks:
arm controllers, GenICam devices through the installed CTI, OPC-UA endpoints
(browsed into a candidate `tags:` inventory), serial ports. Output is a discovery
report plus **draft `resources:` blocks**. Anything ambiguous (which of two cameras
is the fixed one) goes back on the questionnaire.

**Phase 2 — Draft and boot in sim.** Write `cell.yaml` + `runtime/sim.yaml` +
`runtime/live.yaml`; `wfctl cell validate` against the schema; activate the **sim**
overlay and confirm every device reaches `alive` with a plausible state. **No
hardware is touched in this phase.**

**Phase 3 — Incremental live bring-up.** One device at a time, using the existing
mixed-overlay mechanism: generate `runtime/bringup-<device>.yaml` where exactly
that device is `live` and everything else is `sim`. For each device, run the
contract **conformance suite** against the live backend, with the recorder rolling.
This is the core safety property of the whole design: *live exposure grows one
device at a time, and the arm is last.* Arm bring-up additionally starts at a
clamped speed scale and inside a reduced joint envelope until its checks pass.

**Phase 4 — Geometry and calibration.** CAD/scene import; frame touch-off; TCP
definition; camera intrinsics; hand-eye. The agent drives each procedure and the
human performs the physical steps (place the board, jog to the touch point) —
these are guided actions with a UI panel and a CLI equivalent, not autonomous
motion. Results land in the config store with `source` and residual, and are
snapshotted to `snapshots/`.

**Phase 5 — Vision pipelines.** Author a pipeline per detection task, tune it
against **recorded** frames from phase 3/4 (never against the live camera in a
loop), register its outputs as dynamic frames, and lock in a replay regression
(`wfctl vision-eval`) as its test.

**Phase 6 — Program.** Author the `Program`. Verify in sim against a **scenario**
(forced inputs, injected faults — the existing `force` on inputs is ungated exactly
for this). Then live at a clamped speed scale, then at target speed.

**Phase 7 — Acceptance.** Run `acceptance.yaml` for N cycles, produce the report,
`snapshot` operational state back into the deployment dir, commit.

Human gates (non-negotiable, cannot be auto-approved): first live power to each
device (phase 3), every calibration write (phase 4), the first live program run
(phase 6), and sign-off on the acceptance report.

### 3. Loop B — the cell steward

Runs continuously against a commissioned cell. Its input is a **rolling window of
the cell's own observability**, not polling: `{realm}/events`, aborts, supervisor
`exited` events with a non-zero code, audit records with `ok: false`, log lines at
ERROR, motion rejections, vision confidence below threshold, and metric drift.

**Triage** — every incident is classified into exactly one of:

| Class | Signature | Action |
|---|---|---|
| **Cell** | pose/frame drift, a program guard that is wrong, a pipeline threshold, a scene object missing, a param out of range | Fix in the deployment dir. Reproduce from the incident recording, fix, verify in sim + replay, propose a diff, apply through the gate. |
| **Platform** | a HAL traceback, a contract violation, a core service crash, a reproducible driver misbehaviour | **GitHub issue on `theveloped/endesha`** with the evidence bundle (below). Never patched from the cell. |
| **Physical** | device unreachable, protective stop with no software cause, a machine fault code, a sensor reading out of physical range | Notify the human; the agent does not attempt a fix. |

**The evidence bundle** is the thing that makes a filed issue actionable, and it is
the reason the observability work in Part IV step 1 comes first: an incident
recording slice (MCAP, ±60 s around the event), the merged log tail from every
service, the audit records for the commands involved, the execution snapshot of
the offending goal, the program graph with the active state marked, the cell +
runtime YAML, and the platform version. All of it already exists on the bus — it
just needs a command that packages it.

**Hill climbing** is a separate, slower cadence than incident response, and it is
strictly bounded by §III.6.

### 4. Acceptance and objectives as data

`acceptance.yaml` turns the requirements document into machine-checkable criteria,
and doubles as the hill-climbing objective:

```yaml
objectives:
  cycle_time_s:      {target: 12.0, direction: min, weight: 1.0}
  pick_success_rate: {target: 0.995, direction: max, weight: 3.0, hard: true}
  locate_residual_mm:{target: 0.5,  direction: min, weight: 1.0}
constraints:
  - no_collision_rejections
  - no_safety_aborts
  - max_speed_scale: 1.0
sample:
  cycles: 50                # a run is only comparable at this sample size
```

`hard: true` means a regression is disqualifying regardless of the weighted score.

### 5. Metrics — computed offline over recordings

Deliberately **not** a new online service. A run's metrics are computed from its
MCAP by the same code that computes them from a replay, which makes runs
comparable by construction and makes the whole scoreboard reproducible from the
artefacts already in `journal/`. Derived from `program/transitions` (state dwell,
cycle boundaries), arm goal `result`/`snapshot` (planned vs. actual move duration,
rejections), `{realm}/events` (aborts by class), `{realm}/audit/**` (command
latency, failures), and vision results (latency, confidence, residual).

### 6. The tuning envelope — how hill climbing stays safe

Nothing is tunable unless it is *declared* tunable. `tuning.yaml`:

```yaml
knobs:
  program.demo_pick.settle_s:      {range: [0.05, 0.8],  step: 0.05, risk: low}
  pipeline.locate_part.min_score:  {range: [0.4, 0.9],   step: 0.02, risk: low}
  cell.r1.ruckig_defaults.vmax[*]: {range: [0.5, 2.0],   step: 0.1,  risk: high}
  pose.pick_approach.z:            {range: [-0.01, 0.01],step: 0.002,risk: medium}
policy:
  low:    {auto_promote: true,  max_delta_per_step: 0.1}
  medium: {auto_promote: false, max_delta_per_step: 0.05}
  high:   {auto_promote: false, max_delta_per_step: 0.02, requires: human}
```

The experiment protocol, per candidate change:

1. **Simulate.** Run the objective in sim. A candidate that loses in sim is dropped
   without ever touching the cell.
2. **Replay-regress.** For vision changes, re-run the pipeline over the labelled
   recording set. A candidate that regresses any labelled frame is dropped.
3. **Live trial.** One knob at a time, one step at a time, `sample.cycles` cycles,
   with the recorder marking the experiment window. **Any abort, any collision
   rejection, any hard-objective regression → immediate revert to baseline.**
4. **Decide.** Promote only on a weighted-score improvement outside run-to-run
   noise, with no hard-objective regression. `risk: low` promotes automatically;
   everything else opens a PR against the deployment dir with the metrics diff as
   the body.

Two invariants: **the agent never writes to a live cell outside an experiment
envelope**, and **every experiment is a recorded, revertible, single-knob step**.

### 7. Capability tiers

`wfctl` and the agent's tooling honour `WF_AGENT_MODE`:

| Mode | Allowed |
|---|---|
| `read` | subscribe, query, read recordings. Nothing else. Default. |
| `sim` | everything, but only while the active runtime overlay has no `live` device. |
| `live-gated` | live writes limited to the declared experiment envelope; safety-relevant commands and calibration writes require an explicit human approval token. |

The steward runs in `read` and escalates to `sim` to reproduce, and to `live-gated`
only inside an approved experiment.

---

## Part IV — Delivery order

Each step is independently useful and independently testable. Steps 1–3 are what
turn the existing platform into something an agent can *operate*; they are worth
doing regardless of how far the rest goes.

**1. Make the cell legible headlessly.** `wf.core.events.emit_event()` →
`{realm}/events` — specified in detail in `event-ledger-rfc.md` (the record
schema, the durable ledger, retention, and how an incident becomes a regression
test); adopted in control acquire/release, program
load/start/complete/abort, supervisor spawn/exit, safety stop, config write,
source switch, recording mark. `QueryAudit` on the remaining queryables (camera2d,
washer, recorder) and capture every reply, not just the first. New `wfctl`
commands: `events`, `logs [-f] [--service]`, `queries [-f]`, `topics`, `health`
(one JSON: every service and device's liveliness, unit state, lease owner, recent
errors). New `wf.tools.mcapq`: `topics | slice | grep | timeline | stats` over a
recording. Rolling recorder: `--rolling <minutes>` ring plus `--snapshot-on <kind>`.

**2. Structured failures and a metrics scoreboard.** A failure taxonomy
(`{code, category, severity, source, context}`, category ∈
`safety|motion|device|program|vision|config|platform`) emitted as an event
alongside today's reason strings. `wfctl metrics <recording>` computing the §III.5
set into a JSON next to the MCAP, and `wfctl metrics-diff a.json b.json`.

**3. Give the agent a home.** Root `CLAUDE.md` + `platform/CLAUDE.md`.
`.claude/skills/{commission-cell,cell-steward,program-author,vision-pipeline}`.
`.github/workflows/ci.yml` running `pytest`, `tsc -b`, `npm run build`,
`docker compose config --quiet`. A Linux `deploy/start_stack.sh` mirroring the
PowerShell launcher. `WF_AGENT_MODE` enforcement in `wfctl`. An `incident-bundle`
command that packages §III.3's evidence bundle, and the issue template it fills.

**4. Commissioning machinery.** `wfctl probe --arm|--genicam|--opcua|--serial`
emitting paste-ready `cell.yaml` fragments. A JSON schema for `cell.yaml` plus
`wfctl cell validate` and `wfctl cell doctor` (validate + dry-spawn each provider).
`bringup-<device>.yaml` overlay generation. Contract conformance suites runnable
against a live backend.

**5. The vision layer.** `wf.contracts.vision`
(`{realm}/vision/{pipeline}/{result,overlay,state/status}`, `cmd/{configure,run}`),
overlays as *data* not pixels so the UI renders any pipeline generically.
`{realm}/frames/{name}` dynamic frames with confidence + TTL, merged into the live
tree with a short time buffer so `t_capture` resolution is correct.
`wf.services.vision`: a pipeline runtime shaped like the program runner (declared
inputs/params/outputs, directory discovery, hot reload, sim/live/replay agnostic
because it consumes the camera contract). `VisionProxy` so a program can write
`self.m.locator.locate()` and then `move_j(frame="pallet_1", ...)`.
`wfctl vision-eval <pipeline> <recording>` — the replay regression harness, which
is simultaneously the vision test suite and the hill-climbing scorer.

**6. The calibration service** (design v5 §5.5): intrinsics from a board capture,
hand-eye into `config/arm/{rid}/tcp/{cid}_optical`, 3-point touch-off frames. Each
as a guided action with a residual, driveable from CLI or UI.

**7. The experiment engine.** `tuning.yaml` + `acceptance.yaml` schemas.
`wfctl experiment` (baseline → variant → N cycles → metrics diff → promote/revert),
recorder marks around every trial, auto-revert on any abort, PR-on-promotion for
`medium`/`high` risk knobs. Wire `Waypoint.speed`/`.accel` through so per-move
speed is actually tunable (gap 16).

**8. Cell types and skills** (design v5 §8) — only once a second cell would share
something. Premature before that.

---

## Open questions

1. **Which cell is the first target?** The Ecoclean washer cell exists and is
   waiting to be commissioned live over OPC-UA (`deploy/ecoclean/runtime/live.yaml`)
   — it needs steps 1–4 and nothing else, and would validate Loop A end to end
   without any vision work. A vision-guided pick cell needs step 5 and 6 first,
   which is a much longer runway. **Recommendation: prove Loop A on Ecoclean, then
   build the vision layer for the pick cell.**
2. **Where does the agent run?** On the cell box (reaches hardware, but then the
   box needs outbound network for GitHub and model access) or remote against the
   bus (the zenoh router is already reachable, but recordings are large)? This
   decides whether step 3's Linux launcher is on the critical path.
3. **Is `fleet/` a directory in this repo or a second repo?** Design v5 §8.6
   proposes two repos. Starting as `fleet/` here is cheaper and the split stays
   cheap because the tier boundary is directory-shaped.
4. **How autonomous should the steward be by default?** The design above defaults
   to: cell-level fixes proposed as diffs and applied through a gate; only
   `risk: low` tuning promotes without a human. Loosening that is a policy change,
   not a code change.
