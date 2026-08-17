# Writing programs (`wf.program`)

A program is a Python file in `deploy/programs/` defining one
`wf.program.Program` subclass (a [python-statemachine](https://python-statemachine.readthedocs.io/)
`StateChart`). The program runner discovers it, the Programs tool (or `wfctl`)
loads it into the cell's PackML unit, and it runs unchanged against simulated,
live or replayed devices — it only ever talks to devices through *roles*.

Edit in the browser (Programs → **new / edit**, Ctrl/Cmd+S saves and reports
import errors) or in your IDE; a save is picked up by the next Load.

```python
from wf.program import Program, State, after, on_channel

class PickAndPlace(Program):
    """Shown in the catalog."""
    program_name = "pick_and_place"                 # catalog name (default: file stem)
    roles = {"arm": "arm", "io": "dio"}             # role -> device contract
    params = {"cycles": 3, "approach": "pick_approach"}   # defaults, overridable at Load
    triggers = [
        on_channel("io", "part_present", edge="rising", event="part_arrived"),
        after(20.0, state="waiting", event="feeder_quiet"),
    ]

    waiting = State(initial=True)
    picking = State()
    done = State(final=True)

    part_arrived = waiting.to(picking)
    picked = picking.to(done, cond="last_cycle") | picking.to(waiting)
    feeder_quiet = waiting.to(done)

    def __init__(self, roles, params, runtime):
        self.count = 0
        super().__init__(roles, params, runtime)

    def last_cycle(self):                             # guard: plain method returning bool
        return self.count >= int(self.p["cycles"])

    def run_picking(self, ctx):                       # ACTION of state `picking`
        self.m.arm.move_j(self.p["approach"])
        self.m.io.set("gripper", True)
        ctx.sleep(0.3)
        self.count += 1
        self.log(f"picked {self.count}")
        self.emit("picked")

PROGRAM = PickAndPlace   # optional when the file has exactly one Program subclass
```

## Class attributes

| attribute | meaning |
|---|---|
| `program_name` | catalog name. **Not** `name` — python-statemachine owns that. Default: file stem. |
| `roles` | `{role: contract}`. Contracts today: `arm`, `dio`. Bound to device ids at Load (default: the sole device of that contract; else pick in the UI / `--bind role=rid`). |
| `params` | defaults; overridden at Load (`--param k=v`, JSON values). Available as `self.p[...]`. Unknown keys are rejected at Load. |
| `triggers` | declarative event sources evaluated by the runner (see below). |

Reserved names you must not reuse for states/events: anything python-statemachine
defines (`name`, `states`, `events`, `send`, `configuration`, `current_state`,
`start`, …) and the `Program` API (`m`, `p`, `emit`, `log`, `run_*`, `on_*`).

## States, transitions, guards

Plain python-statemachine:

- `x = State(initial=True)`, `State()`, `State(final=True)`. Reaching a final
  state completes the unit (PackML → Complete). Every non-final state must have
  at least one outgoing transition (import error otherwise).
- `event = a.to(b) | c.to(d)`; guards with `cond="method_name"` /
  `unless="method_name"` (methods returning bool, may use `self.p`, `self.m`).
- Compound / parallel states and history states work as in python-statemachine
  3.x; actions run for every active leaf state.
- Do **not** call `self.send()` from an action thread — use `self.emit()`.

## Actions

`def run_<state_id>(self, ctx)` is the state's action:

- Starts when the state is entered **while the unit executes**; runs on its own
  thread. A state without `run_` is passive (waits for an event).
- **Cancelled when the state is left** — by a transition, by Hold/Suspend/Stop/
  Abort, by an e-stop. Blocking proxy calls raise `ActionCancelled`; long loops
  should call `ctx.check()`; use `ctx.sleep(s)` instead of `time.sleep`.
  Let `ActionCancelled` propagate.
- After **Unhold/Unsuspend** the interrupted state's action re-runs from the
  top (there is no resume-in-the-middle yet).
- Any other exception aborts the unit with reason
  `action_error:<state>:<message>` (`ProgramError`) or
  `action_crash:<state>:<repr>`.
- `ctx`: `ctx.check()`, `ctx.sleep(seconds)`, `ctx.cancelled`,
  `ctx.on_cancel(fn) -> unregister`, `ctx.log(msg)`, `ctx.state_id`.

## Events

- `self.emit(event, **data)` from anywhere (usually the end of an action).
- Triggers: `on_channel(role, channel, edge="rising"|"falling"|"change", event=...)`
  fires on a dio channel value change; `after(seconds, state=..., event=...)`
  fires `seconds` after `state` was entered (cancelled if it is left first).
- External: `wfctl program-event NAME` / Programs tool "Send event" /
  `program/cmd/event` on the bus.
- Events are only delivered while the unit is in Execute; an event without a
  matching transition from the current state is ignored.

## Device API (`self.m.<role>`)

### arm

| call | notes |
|---|---|
| `move_j(target, *, speed=None, accel=None, timeout_s=120)` | joint move. `target`: pose **name** (`config/programs/<prog>/poses/<n>` first, then `config/poses/<n>`), a 6-list `q`, a `Pose`, or `frame="name", xyz=[..], quat=[..]` (Cartesian target for the active TCP; `free=` for a loose DOF). |
| `move_l(...)` | same targets, straight Cartesian line. Needs a Cartesian target (a Pose/frame, **not** a joint pose name). |
| `move_path([Waypoint, …])` | several waypoints as one goal (blend radii). |
| `set_tcp(name)` | select the active TCP from the config store. |
| `stop()` | out-of-band stop. |
| `q` | latest joints (list or None); `status` — latest `ArmStatus`. |

Motion is rejected (→ abort) with `motion_rejected:<reason>` when the driver
refuses (no lease, protective stop, `target_outside_limits`, collision, …).

### dio

| call | notes |
|---|---|
| `get(name)` | current value (bool / float). |
| `wait(name, value=True, *, timeout_s=None)` | block until `== value` (or `value(current)` when callable); returns False on timeout, raises on cancel. |
| `set(name, value)` | write an OUTPUT (needs the lease the program holds). |
| `force(name, value)` / `force(name, None)` | override / clear a channel's reported value (test scenarios). |
| `pulse(name, seconds=0.2)` | set on, wait, set off. |
| `snapshot()` | `{name: value}`. |

Channel names come from `cell.yaml` (`channels:` / `provides:`); unmapped
physical pins are also addressable by their auto names (`di3`, `tool_do0`).

### other (`self.m` helpers)

`self.m.pose("name")` resolves a pose (same order as `move_j`);
`self.m.bindings` is the role→device-id map; `self.m["role"]` equals attribute
access; `self.m.device("io1")` reaches a device outside the bindings;
`self.m.ids("dio")` lists device ids. These helper names (`pose`, `device`,
`ids`, `rid`, `bindings`, `machine`) are reserved — Load rejects a role with
such a name (`bind:<role>:reserved_role_name`).

## Unit hooks (optional overrides)

`on_hold()`, `on_resume()`, `on_stop()`, `on_abort(reason)` — called on the
driver thread when the unit changes; keep them short. Hold/Stop/Abort/Reset
themselves are unit-level and never appear in the program's states.

## Runtime rules

- While the unit is not Idle/Stopped/Aborted/Complete the **program holds the
  cell control lease** as `program:<name>:<id>` — the UI cannot jog or set
  outputs meanwhile. Forcing an **input** never needs the lease (feed parts in sim).
- An arm e-stop or protective stop aborts the unit (`safety:*`); a lost lease
  aborts too (`lease_lost:*`).
- Programs are recorded (`program/state|transitions|log`) like every realm topic.

## Debugging

- Programs tool: **Waiting for** (armed triggers / accepted events of the
  active state), **Log** (`self.log`, runner notes, abort reasons),
  **Transitions**; `wfctl program-state`, `wfctl program-log -f`.
- Load errors: `unknown_program`, `program_broken:<import error>`,
  `unknown_params:x`, `bind:<role>:...`, `invalid_in_state:<unit>`.

## Not (yet) supported

Program-scoped frames, resumable actions after Hold, other device contracts
(serial / OPC-UA / HTTP), variables persisted across runs, and multiple units
per cell.
