"""Demo pick-and-place: wait for a part, pick it, drop it on the belt, repeat.

Cell-agnostic: needs one ``arm`` and one ``dio`` with channels ``part_present``
(di), ``gripper`` and ``conveyor_run`` (do). The named poses it moves through
are params (``home``, ``approach``, ``grasp``, ``place``) so the same program
runs in any cell that has poses under those names in the config store. Runs
unchanged against the simulated or the live cell — in sim, force
``part_present`` on the IO page (or ``wfctl dio-force part_present on``) to
feed it parts.
"""

from wf.program import Program, State, after, on_channel


class DemoPick(Program):
    """Pick parts from the feeder while parts keep arriving; stop after `cycles`."""

    program_name = "demo_pick"
    roles = {"arm": "arm", "io": "dio"}
    params = {
        "cycles": 3,
        "settle_s": 0.5,
        "home": "home",
        "approach": "pick_approach",
        "grasp": "pick_grasp",
        "place": "inspect_a",
    }
    triggers = [
        on_channel("io", "part_present", edge="rising", event="part_arrived"),
        # Nothing arrived for a while: go home and idle instead of hovering.
        after(20.0, state="waiting", event="feeder_quiet"),
    ]

    homing = State(initial=True)
    waiting = State()
    picking = State()
    placing = State()
    parked = State()
    done = State(final=True)

    homed = homing.to(waiting)
    part_arrived = waiting.to(picking) | parked.to(picking)
    picked = picking.to(placing)
    placed = placing.to(done, cond="cycles_left_none") | placing.to(waiting)
    feeder_quiet = waiting.to(parked)

    def __init__(self, roles, params, runtime):
        self.count = 0
        super().__init__(roles, params, runtime)

    # ── guards ───────────────────────────────────────────────────────────

    def cycles_left_none(self) -> bool:
        return self.count >= int(self.p["cycles"])

    # ── actions (each runs on its own thread; cancelled when the state is left)

    def run_homing(self, ctx):
        self.m.io.set("gripper", False)
        self.m.arm.move_j(self.p["home"])
        self.emit("homed")

    def run_waiting(self, ctx):
        # Passive wait; the trigger fires part_arrived. Keep the belt running.
        self.m.io.set("conveyor_run", True)

    def run_picking(self, ctx):
        self.m.io.set("conveyor_run", False)
        # Named poses are joint poses -> move_j. (move_l needs a Cartesian
        # target: a Pose, or frame=... with an offset.)
        self.m.arm.move_j(self.p["approach"])
        self.m.arm.move_j(self.p["grasp"])
        self.m.io.set("gripper", True)
        ctx.sleep(float(self.p["settle_s"]))
        self.m.arm.move_j(self.p["approach"])
        self.emit("picked")

    def run_placing(self, ctx):
        self.m.arm.move_j(self.p["place"])
        self.m.io.set("gripper", False)
        self.count += 1
        self.log(f"placed part {self.count}/{self.p['cycles']}")
        self.emit("placed")

    def run_parked(self, ctx):
        self.m.io.set("conveyor_run", False)
        self.m.arm.move_j(self.p["home"])

    # ── unit hooks ───────────────────────────────────────────────────────

    def on_abort(self, reason: str) -> None:
        self.log(f"aborted: {reason}")


PROGRAM = DemoPick
