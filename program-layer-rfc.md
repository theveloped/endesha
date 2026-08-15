# RFC — Program layer, first-class devices, and platform polish

Status: **draft for review** (2026-08-15). Branch: `platform-bare-minimum`.
Builds on the completed selectable-source refactor (`cell.yaml` + runtime overlays,
supervisor as provider orchestrator, per-device live/sim/replay).

## 0. Decisions already taken (not up for discussion here)

- Programs are **code-first `python-statemachine` StateCharts** (Vention "Python
  application" style). No React Flow, no behaviour trees. A visual layer may come
  later purely as visualization / low-code and may look different.
- **PackML unit states live in the runner**, never in user programs.
- **All device types are first-class contracts** with named channels. The arm is
  a peer, not the centre. A cell with no arm (e.g. two serial testers) must work.
- Only the `dio` contract is built now. `serial` / `opcua` / `http` follow the same
  pattern later and are referenced only to make sure the pattern fits them.
- The arm's onboard IO is exposed **as a `dio` device** (facade), so programs have
  one IO API.
- Also in scope: nominal-vs-calibrated frames, CameraInfo `K`/`D`, SRDF vocabulary
  (not storage), Vention-style non-blocking transitions with cancel-on-exit,
  application-scoped assets, and the UI structural fixes (AppShell split, router,
  resize-aware layout).

## 1. Goals / non-goals

Goals

1. Author an automation as Python, run it unchanged against `sim`, `live` and
   `replay` sources by only changing the runtime overlay.
2. Every external interaction (arm, IO, later serial/OPC-UA/HTTP) is a logical
   device with a contract, named channels, and a sim provider — so any program
   is simulatable end to end.
3. Operator-facing control follows PackML vocabulary (Start / Hold / Stop /
   Abort / Reset …) and is inspectable on the bus.
4. Everything the program does is recorded by the existing recorder because it
   lives under the realm prefix; replay shows the program timeline for free.

Non-goals (now)

- Graph/visual authoring, behaviour trees, parallel program regions beyond what
  a statechart gives.
- Serial / OPC-UA / HTTP providers (design must accommodate; code later).
- Multi-node distribution beyond what `node:` already carries.
- Full HMI builder. A minimal operator page only.

## 2. Devices: the `dio` contract and named channels

### 2.1 Cell schema additions

```yaml
resources:
  r1:                     # unchanged arm resource
    contract: arm
    ...

  io0:                    # NEW: the arm's onboard IO exposed as a dio device
    contract: dio
    model: aubo_onboard
    config:
      channels:           # named channels; programs ONLY use these names
        part_present:  { kind: di, bank: standard, pin: 3 }
        door_closed:   { kind: di, bank: standard, pin: 4 }
        clamp:         { kind: do, bank: standard, pin: 0 }
        gripper:       { kind: do, bank: tool,     pin: 0 }
        pressure:      { kind: ai, index: 0, unit: bar, scale: 0.1 }
    sources:
      live: { kind: arm_dio, params: { arm: r1 } }   # facade over r1's io slice
      sim:  { kind: sim_dio, params: {} }             # standalone, all inputs forceable
```

- `channels` is contract-agnostic in shape (`name -> {kind, address…}`) so
  `serial`/`opcua` reuse it (`kind: node`, `kind: register`, …).
- `_CONTRACTS` in `supervisor/cell.py` gains `dio`; `_MODES` unchanged.
  `devices_inventory()` already carries `config`, so the UI device tree gets
  channels without new plumbing.
- Channel names are validated at cell load: `[a-z][a-z0-9_]*`, unique per device.

### 2.2 Keys (`wf.contracts.dio.keys`)

```
{realm}/dio/{rid}/state/channels     pub, latest-wins, on change + 1 Hz keepalive
{realm}/dio/{rid}/cmd/set            queryable  {channel, value}            -> Ack
{realm}/dio/{rid}/cmd/force          queryable  {channel, value|null}       -> Ack
{realm}/dio/{rid}/alive              liveliness token
```

Payload of `state/channels`:

```json
{"t": 0, "channels": {"part_present": {"kind":"di","value":true,"forced":false},
                      "clamp":        {"kind":"do","value":false,"forced":false},
                      "pressure":     {"kind":"ai","value":4.2,"forced":false}}}
```

- `cmd/set` writes outputs only (`do`/`ao`); inputs reject with `read_only`.
- `cmd/force` overrides any channel's *reported* value (PLC "force" semantics),
  `value: null` clears. Forced channels are flagged so the UI can show it. This is
  the ONE mechanism that makes simulation meaningful: `sim_dio` is simply a
  provider where nothing is wired, so every input is driven by force. Forcing is
  allowed on live too (behind the same control lease as motion — see 2.4).
- Kinds: `di`, `do`, `ai`, `ao`. Bit-packing disappears from the program-facing
  surface; it stays inside the arm facade.

### 2.3 Providers

- `wf.hal.dio_core` — `DioCore` serves the contract (channel table, force
  overlay, publish-on-change, keepalive) + `DioBackend` ABC
  (`read() -> {name: value}`, `write(name, value)`). Mirrors `arm_core`.
- `wf.hal.arm_dio` — backend that subscribes `arm/{rid}/state/io` and calls
  `arm/{rid}/cmd/set_do`. Pure bus client; works over live *or* sim arm.
- `wf.hal.sim_dio` — backend with in-memory values; optional `script:` param
  (`[{at_s: 2.0, set: {part_present: true}}, …]`) for repeatable scenarios.
- `replay` — `state/channels` is recorded like any topic; a `replay_dio`
  backend is a trivial `LoopPlayer` republish, same as `replay_arm`.
- Conformance tests in `contracts/dio/conformance/` run against every backend
  (pattern from `contracts/arm/conformance`).

### 2.4 Authority: one cell-level control lease

**Decision:** one operator holds the lease for ALL devices in the cell. The lease
moves out of `ArmCore` into a cell-wide authority hosted by the supervisor (the
always-on, one-per-cell process). `wf.core.lease.ControlLease` is reused as is.

```
{realm}/control/cmd/acquire      queryable {client_id, user}   -> ControlAck
{realm}/control/cmd/release      queryable {client_id}         -> ControlAck
{realm}/control/state/owner      pub latest-wins ControlOwnerState (+ on every grant/renew/release/expiry)
{realm}/control/alive            liveliness token of the authority
```

- Providers (`ArmCore`, `DioCore`, later serial/opcua/http) subscribe
  `control/state/owner`, query it once on start, and treat a missing
  `control/alive` as "no lease" → every guarded command is rejected with
  `no_lease`. They never grant.
- Guarded: arm jog / execute_path (as today) and dio `set` / `force` (step 1).
  Arm `set_do` / `set_tcp` / `clear_protective_stop` are NOT lease-gated today
  (their requests carry no `client_id`); `set_do` disappears behind the dio
  facade, the other two get gated when the arm messages grow a `client_id`
  (follow-up, not part of step 0). Read-only queries and `stop` are never
  guarded (`stop` must always work).
- Arm keys `cmd/acquire_control`, `cmd/release_control`, `state/control_owner`
  are **removed** (no back-compat: single deployment, single UI); UI
  `RuntimeProvider`, `wfctl`, arm conformance tests and `browser_camera` move to
  the `control/` keys. `ArmCore` keeps its `client_id` checks, sourced from the
  subscription instead of the local `ControlLease`.
- The program runner acquires the cell lease under the program's `client_id`
  at `Starting` and renews while not Idle/Stopped/Aborted; the operator UI
  therefore cannot hold it while a program runs (by design — one holder).

### 2.5 Arm contract

`arm/…/state/io` and `cmd/set_do` remain (drivers, `IoPage`, tests). The UI
`IoPage` moves to `dio` channels; the raw arm io view stays only in Topics. The
arm `IoState` is deprecated for programs — programs never import it.

## 3. Program layer

Two packages: `wf.program` (SDK, no zenoh in user-facing types) and
`wf.services.program_runner` (one process, PackML unit machine, discovery, bus).

### 3.1 The `Machine` facade (SDK)

Built from the supervisor's `devices` inventory; one typed proxy per contract.
Only speaks contract keys → identical under live/sim/replay.

```python
m.arm("r1").move_j(pose="pick_above", speed=0.5)          # named pose (program- or cell-scoped)
m.arm("r1").move_l(frame="tray/slot_3", xyz=[0,0,0.02], quat=[0,0,0,1])
m.arm("r1").move_j(q=[...])
m.dio("io0").set("clamp", True)
m.dio("io0").get("part_present")
m.dio("io0").wait("part_present", True, timeout_s=10)
m.dio("io0").force("part_present", True)                   # sim/testing only by convention
```

- Every blocking call is a goal/query with a *cancellation token* from the
  running action (see 3.3); cancel → raises `ActionCancelled` inside user code.
- The facade acquires/renews the control lease under the program's `client_id`
  (`leaves.py` from `e37c803^` already does this — recover and split per contract).
- Proxies for future contracts (`m.serial("tester")`, `m.opcua("plc")`) are added
  by registering `contract -> proxy` — no runner change.

### 3.2 A program

```python
from statemachine import State
from wf.program import Program, on_channel

class PickAndPlace(Program):
    """Cell-agnostic; roles bind to device ids at load (see 3.5)."""
    roles = {"arm": "arm", "io": "dio"}
    params = {"cycles": 10, "approach_z": 0.05}          # start-time overridable

    waiting = State(initial=True)
    picking = State()
    placing = State()
    done = State(final=True)

    part_arrived = waiting.to(picking)
    picked  = picking.to(placing)
    placed  = placing.to(waiting, unless="cycles_left") | placing.to(done, cond="cycles_left")

    # declarative event sources (evaluated by the runner, not user code)
    triggers = [on_channel("io", "part_present", edge="rising", event="part_arrived")]

    def on_enter_picking(self, ctx):
        self.m.arm.move_j(pose="pick_above")
        self.m.io.set("clamp", True)
        self.m.arm.move_l(pose="pick", speed=0.2)
        self.m.io.set("gripper", True)
        self.send("picked")

    def on_enter_placing(self, ctx): ...
```

- `Program` is a `StateChart` subclass with `self.m` (bound facade), `self.p`
  (params), `self.send()` and `self.log()`. Nothing PackML-related is visible.
- `on_enter_*` handlers **run on a worker thread** and receive `ctx` (cancel token
  + `ctx.check()`); they are the "action sequence" of the state.

### 3.3 Transition semantics (Vention model + cancel-on-exit)

- Transitions are **non-blocking**: an event is processed immediately by the
  single driver thread even if the current state's action is still running.
- **Leaving a state cancels its running action**: the runner cancels the active
  goal(s) via `wf.core.action` cancel and sets the token; the action thread
  unwinds with `ActionCancelled`. The next state's action starts only after the
  previous thread has joined (bounded, else the unit machine goes to Aborting
  with `reason: action_hang`).
- Actions must not call `self.send` after they were cancelled (the SDK swallows
  it and logs).
- Events come from: user code (`self.send`), declarative `triggers`
  (channel edges, timers), HMI/bus (`cmd/event`), and the unit machine (Hold,
  Stop, Abort are *not* program events; they act on the unit).

### 3.4 Unit machine (PackML, in the runner)

States: `Idle, Starting, Execute, Completing, Complete, Holding, Held, Unholding,
Suspending, Suspended, Unsuspending, Stopping, Stopped, Aborting, Aborted,
Clearing, Resetting`. Commands: `start, hold, unhold, suspend, unsuspend, stop,
abort, clear, reset`. Implemented once with `python-statemachine`.

Mapping to the program:

| Unit transition | Effect on program |
|---|---|
| Starting → Execute | construct program with facade + params; enter initial state |
| program reaches a `final` state | Execute → Completing → Complete |
| `hold` | cancel active action, remember current state; on `unhold` re-enter it (entry action re-runs) |
| `suspend` | same mechanics as hold; used by triggers such as `door_closed == False` (declared per program: `suspend_when=[...]`) |
| `stop` | cancel, discard program → Stopped; `reset` → Idle |
| `abort` / arm `estop` / `protective_stop` / uncaught exception in an action | cancel, discard → Aborted (`reason` recorded); `clear` → Stopped |

Arm status is watched by the runner (`state/status`) so an e-stop always aborts
the unit even if the program is mid-`wait`.

### 3.5 Keys (`wf.contracts.program.keys`)

```
{realm}/programs/catalog                 pub latest-wins + queryable: [{name, roles, params, doc}]
{realm}/programs/cmd/load                queryable {name, bindings:{role: rid}, params} -> Ack   (unit must be Idle/Stopped)
{realm}/program/state                    pub latest-wins: {t, unit, program, program_state, action, reason, params, bindings}
{realm}/program/cmd/{start|hold|unhold|suspend|unsuspend|stop|abort|clear|reset}   queryables -> Ack
{realm}/program/cmd/event                queryable {event, data} -> Ack   (HMI/bus → program)
{realm}/program/transitions              pub, every unit/program transition (event log; DROP is fine)
{realm}/program/alive
```

One loaded program per unit; one unit per runner; one runner per cell for now
(the singular `program/` prefix mirrors that; `program/{unit}/…` is a later
extension if a cell ever needs two units).

### 3.6 Discovery and role binding

- Programs are Python modules under `deploy/programs/` (or any dir passed with
  `--programs`). A module exposes `PROGRAM = PickAndPlace`. Import errors surface
  in the catalog entry, never crash the runner.
- `roles` (contract per role) bind to device ids at `cmd/load`. Default binding:
  the sole device of that contract in the inventory; otherwise required.

### 3.7 Application-scoped assets and params

- Config store gains a family `config/programs/{name}/poses/{p}`,
  `config/programs/{name}/frames/{f}` (same validators as the cell families).
  Resolution order in the facade: program-scoped, then cell-scoped. The Frames
  page shows program assets in their own group; they travel with the program.
- `params` are declared with defaults in code, overridable at `cmd/load`, and
  published in `program/state`. Assets may reference params later (Vention's
  "expression targets"); v1 keeps assets literal.

## 4. Frames: nominal vs calibrated

`FrameDef` (`wf.core.frametree`) gains:

```python
nominal: dict | None = None      # {"xyz": [...], "quat": [...]} design value
calibration: dict | None = None  # {"t": ns, "method": str, "residual": float, "by": str}
```

- `xyz`/`quat` remain the **effective** pose (backwards compatible everywhere:
  tree math, wire, UI).
- Rule: `source: manual` writes both effective and nominal; a calibration write
  updates effective + `calibration` and preserves `nominal`. `frametree` gets
  `drift(name) -> (dxyz_m, dangle_rad)`.
- Store validation accepts the two new optional blocks; UI Frames detail shows
  nominal, calibrated, drift, and a "reset to nominal" action.

## 5. Camera intrinsics: CameraInfo layout

`config/intrinsics/{cid}` becomes ROS `sensor_msgs/CameraInfo`-shaped
(the store already carries `cx, cy`, so this is a reshaping, not new data):

```yaml
width: 1280
height: 800
distortion_model: plumb_bob         # or rational_polynomial
D: [k1, k2, p1, p2, k3]             # [] allowed → ideal pinhole
K: [fx, 0, cx, 0, fy, cy, 0, 0, 1]
R: [1,0,0, 0,1,0, 0,0,1]            # optional, identity default
P: [...]                            # optional, derived from K if absent
```

- Store validator migrates old `{fx,fy,cx,cy,w,h}` on read once and rewrites.
- `cell.yaml` `render:` block for sim cameras stops duplicating optics; the sim
  provider reads `config/intrinsics/{cid}` (nominal) and only keeps `background_gray`.
- `camera2d_core.processing` / the browser renderer take `K` (and ignore `D`
  until a distortion pass exists).

## 6. SRDF vocabulary (keep the store)

No XML. Rename in docs/UI, keep keys:

| Store key | SRDF concept | UI label |
|---|---|---|
| `config/poses/*` | `group_state` | Named joint states |
| `config/arm/{rid}/tcp/*` (`role: tool`) | `end_effector` | End effectors / TCPs |
| — (new) `config/arm/{rid}/collision/disabled_pairs` | `disable_collisions` | Collision exceptions |

`collision.py` keeps its computed adjacency defaults but **merges** the declared
`disabled_pairs` (with a `reason`) — auditable, operator-editable. An
`export --srdf` in `wfctl` is a follow-up once there is a MoveIt/Isaac consumer.

## 7. Web

### 7.1 Structure

- Add a router (hash or history) — `/cell/:tool`, `/cell/programs/:name`,
  `/replay/:sid/...`, `/hmi`. Tool selection stops being local `useState`; deep
  links work.
- Split `shell/AppShell.tsx` into `shell/{AppSidebar,WorkspaceHeader,Panes,
  ToolRoutes}.tsx`; `RightToolPane`'s if-chain becomes a `Record<Tool, Component>`.
- `useLayout()` hook: `window.innerWidth` via a resize listener; remembered
  widths read `localStorage` once in an initializer, not per render.
- Viewport is optional: if the inventory has no `arm`, the centre pane shows the
  device/channel dashboard.

### 7.2 New surfaces

- **Devices → IO**: channel table per `dio` device (name, kind, value, forced),
  set/force controls, force badge. Replaces the pin grid.
- **Programs** tool: catalog, load (bindings + params), PackML command bar,
  current unit/program state, transition log, program assets group.
- **`/hmi`** operator page: unit state, Start/Hold/Stop/Reset/Clear, e-stop
  status, current program state, last error. No scene editing.

## 8. Delivery order

0. **DONE** (`23bfe03`) Cell-level lease: `wf.contracts.control` keys + authority in the supervisor;
   `ArmCore` becomes a checker; arm keys removed; UI/wfctl/tests moved. Small,
   self-contained, and everything after depends on it.
1. **DONE** `dio` contract + `dio_core` + `arm_dio` + `sim_dio` (+ force + script) +
   conformance tests + `_CONTRACTS` + `io0` in `cell.yaml`/overlays + `wfctl dio-*`.
   Web IO channel table.
2. `wf.program` facade (from `leaves.py`) + `Program` base + runner with PackML
   unit + keys + one demo program under `deploy/programs/`, validated in `sim`.
3. Web Programs tool + `/hmi`; router + AppShell split land here because the
   Programs tool needs them.
4. Nominal/calibrated frames; CameraInfo reshaping; `disabled_pairs`.
5. Program-scoped assets in the store + Frames page group.
6. (later) `serial` / `opcua` / `http` contracts, cell-level lease, SRDF export.

Each step: pytest + `tsc -b` + `npm run build` + a sim e2e (`start_stack.ps1
-Runtime deploy/runtime/sim.yaml`).

## 9. Decisions from review (2026-08-15)

1. **Lease is cell-level, one holder for all devices** (§2.4). Introduced as
   step 0.
2. **`hold` re-runs the interrupted state's entry action from the top** in v1.
   Resumable actions are a later increment.

Remaining open (defaulting to the proposal unless objected):

3. Program discovery: plain directory of modules (proposed) vs. Python entry
   points.
4. `force` on a *live* `dio` device: allowed, lease-gated, visibly flagged
   (proposed).
