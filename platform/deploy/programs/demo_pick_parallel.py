"""Demo pick-and-place with the belt as a parallel flow.

Same job as ``demo_pick`` (wait for a part, pick it, place it, repeat for
``cycles``), but the conveyor is its own region inside a parallel state: the
belt always runs until a part is detected, holds while the arm has the part,
and restarts the moment the part is lifted — independent of what the arm is
doing. One event drives both regions: ``part_arrived`` stops the belt *and*
starts the pick; ``picked`` releases the belt *and* moves the arm on to
placing.

Cell-agnostic like ``demo_pick``: needs one ``arm`` and one ``dio`` with
channels ``part_present`` (di), ``gripper`` and ``conveyor_run`` (do); the
named poses are params. In sim, force ``part_present`` on the IO page (or
``wfctl dio-force part_present on``) to feed it parts.
"""

from wf.program import Program, State, after, on_channel


class DemoPickParallel(Program):
    """Pick arriving parts; the belt is a concurrent region feeding the arm."""

    program_name = "demo_pick_parallel"
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
        on_channel("io", "part_present", event="part_arrived"),
        # Nothing arrived for a while: send the arm home. The belt region is
        # not parked — it keeps feeding until a part shows up.
        after(20.0, state="idle", event="feeder_quiet"),
    ]

    # ── belt region: always run until a part shows up, hold while it is picked
    feeding = State(initial=True)
    holding = State()
    belt = State(states=[feeding, holding])

    # ── pick region: the arm's flow
    idle = State(initial=True)
    picking = State()
    placing = State()
    parked = State()
    pick = State(states=[idle, picking, placing, parked])

    homing = State(initial=True)
    running = State(parallel=True, states=[belt, pick])
    done = State(final=True)

    homed = homing.to(running)
    # One event, both regions: the belt stops while the arm starts picking.
    part_arrived = feeding.to(holding) | idle.to(picking) | parked.to(picking)
    # The part is lifted: the belt may feed again while the arm places.
    picked = picking.to(placing) | holding.to(feeding)
    # The belt region remembers a part that arrived while the arm was placing:
    # if it is holding one, pick it straight away instead of idling.
    placed = placing.to(picking, cond="part_waiting") | placing.to(idle)
    feeder_quiet = idle.to(parked)
    finished = running.to(done)

    def __init__(self, roles, params, runtime):
        self.count = 0
        super().__init__(roles, params, runtime)

    # ── guards ───────────────────────────────────────────────────────────

    def part_waiting(self) -> bool:
        """The belt region caught a part while the arm was busy."""
        return "holding" in self.active_state_ids

    # ── belt actions ─────────────────────────────────────────────────────

    def run_feeding(self, ctx):
        self.m.io.set("conveyor_run", True)

    def run_holding(self, ctx):
        self.m.io.set("conveyor_run", False)

    # ── arm actions (each on its own thread; cancelled when the state is left)

    def run_homing(self, ctx):
        self.m.io.set("gripper", False)
        self.m.arm.move_j(self.p["home"])
        self.emit("homed")

    def run_picking(self, ctx):
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
        self.emit("finished" if self.count >= int(self.p["cycles"]) else "placed")

    def run_parked(self, ctx):
        self.m.arm.move_j(self.p["home"])

    def run_done(self, ctx):
        self.m.io.set("conveyor_run", False)

    # ── unit hooks ───────────────────────────────────────────────────────

    def on_abort(self, reason: str) -> None:
        self.log(f"aborted: {reason}")


PROGRAM = DemoPickParallel
