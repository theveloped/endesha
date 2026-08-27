"""Ecoclean wash cycle: open for loading, wait for the operator, close and
wash, open for unloading, wait for the operator, close — and again.

Replaces the two-button webapp of the old ecoclean-controller: the operator
confirms "loaded" / "unloaded" with the buttons the HMI offers while the
program waits (``hmi`` labels below), or presses them from the Programs tool.
Every door move is a washer action, so Hold/Stop/Abort (or the "Stop door"
button) releases the door permission and the door stops where it is.

Needs one ``washer``. ``program`` selects the wash program number on the
machine (0 = leave as is); ``cycles`` = 0 runs until stopped.
"""

from wf.program import Program, State


class EcocleanCycle(Program):
    """Load -> wash -> unload, operator-paced, `cycles` times (0 = forever)."""

    program_name = "ecoclean_cycle"
    roles = {"washer": "washer"}
    params = {"cycles": 0, "program": 0, "wash_timeout_s": 3600}
    hmi = {"loaded": "Basket loaded — close & start", "unloaded": "Basket unloaded", "skip": "Skip washing (just close)"}

    checking = State(initial=True)
    opening_to_load = State()
    loading = State()
    washing = State()
    opening_to_unload = State()
    unloading = State()
    closing = State()
    done = State(final=True)

    ready = checking.to(opening_to_load)
    door_open = checking.to(loading) | opening_to_load.to(loading) | opening_to_unload.to(unloading)
    loaded = loading.to(washing)
    skip = loading.to(closing)
    washed = washing.to(opening_to_unload) | checking.to(opening_to_unload)
    unloaded = unloading.to(closing, cond="last_cycle") | unloading.to(opening_to_load)
    closed = closing.to(done)

    def __init__(self, roles, params, runtime):
        self.count = 0
        super().__init__(roles, params, runtime)

    def last_cycle(self) -> bool:
        cycles = int(self.p["cycles"])
        return cycles > 0 and self.count >= cycles

    # ── actions ──────────────────────────────────────────────────────────

    def run_checking(self, ctx):
        w = self.m.washer
        # Come up in any machine state: a stale handshake is cleared with reset.
        if w.phase in ("fault", "door_moving", "initializing"):
            self.log(f"washer in {w.phase}: resetting")
            w.reset()
        if not w.wait_phase({"ready_to_load", "ready_to_unload", "door_open"}, timeout_s=30):
            raise RuntimeError(f"washer not ready: {w.phase}")
        if w.phase == "door_open":
            self.emit("door_open")  # basket accessible: treat as loading position
        elif w.phase == "ready_to_unload":
            self.emit("washed")
        else:
            self.emit("ready")

    def run_opening_to_load(self, ctx):
        self.m.washer.open_door()
        self.emit("door_open")

    def run_loading(self, ctx):
        # Passive: the operator loads the basket and presses "loaded" (or "skip").
        self.log("door open — load the basket, then confirm on the HMI")

    def run_washing(self, ctx):
        w = self.m.washer
        program = int(self.p["program"]) or None
        w.start_wash(program=program)
        self.log(f"washing ({w.status.program if w.status else '?'})")
        if not w.wait_phase("ready_to_unload", timeout_s=float(self.p["wash_timeout_s"])):
            raise RuntimeError("wash cycle timed out")
        self.count += 1
        self.log(f"cycle {self.count} done")
        self.emit("washed")

    def run_opening_to_unload(self, ctx):
        self.m.washer.open_door()
        self.emit("door_open")

    def run_unloading(self, ctx):
        self.log("door open — unload the basket, then confirm on the HMI")

    def run_closing(self, ctx):
        self.m.washer.close_door()
        self.emit("closed")

    # ── unit hooks ───────────────────────────────────────────────────────

    def on_abort(self, reason: str) -> None:
        self.log(f"aborted: {reason}")


PROGRAM = EcocleanCycle
