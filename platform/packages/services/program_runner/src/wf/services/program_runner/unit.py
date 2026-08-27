"""The PackML (ISA-TR88.00.02) unit state machine (program-layer RFC §3.4).

Operator/HMI commands: start hold unhold suspend unsuspend stop abort clear
reset. ``sc`` ("state complete") is the runner's internal event that moves an
acting state (Starting, Completing, Holding, …) on once its work is done;
``program_complete`` is ``sc`` for Execute (the program reached a final
state).

Pure: no bus, no threads. The runner attaches listeners for the actual work.
"""

from __future__ import annotations

from statemachine import State, StateMachine

# States an abort is accepted from (everything but the abort branch itself).
_ABORTABLE = (
    "idle", "starting", "execute", "completing", "complete",
    "holding", "held", "unholding", "suspending", "suspended", "unsuspending",
    "stopping", "stopped", "resetting", "clearing",
)
_STOPPABLE = (
    "idle", "starting", "execute", "completing", "complete",
    "holding", "held", "unholding", "suspending", "suspended", "unsuspending", "resetting",
)


class UnitMachine(StateMachine):
    idle = State(initial=True)
    starting = State()
    execute = State()
    completing = State()
    complete = State()
    holding = State()
    held = State()
    unholding = State()
    suspending = State()
    suspended = State()
    unsuspending = State()
    stopping = State()
    stopped = State()
    aborting = State()
    aborted = State()
    clearing = State()
    resetting = State()

    # operator commands
    start = idle.to(starting)
    hold = execute.to(holding)
    unhold = held.to(unholding)
    suspend = execute.to(suspending)
    unsuspend = suspended.to(unsuspending)
    stop = (
        idle.to(stopping) | starting.to(stopping) | execute.to(stopping)
        | completing.to(stopping) | complete.to(stopping)
        | holding.to(stopping) | held.to(stopping) | unholding.to(stopping)
        | suspending.to(stopping) | suspended.to(stopping) | unsuspending.to(stopping)
        | resetting.to(stopping)
    )
    abort = (
        idle.to(aborting) | starting.to(aborting) | execute.to(aborting)
        | completing.to(aborting) | complete.to(aborting)
        | holding.to(aborting) | held.to(aborting) | unholding.to(aborting)
        | suspending.to(aborting) | suspended.to(aborting) | unsuspending.to(aborting)
        | stopping.to(aborting) | stopped.to(aborting) | resetting.to(aborting)
        | clearing.to(aborting)
    )
    clear = aborted.to(clearing)
    reset = stopped.to(resetting) | complete.to(resetting)

    # internal: acting state finished its work
    sc = (
        starting.to(execute)
        | completing.to(complete)
        | holding.to(held)
        | unholding.to(execute)
        | suspending.to(suspended)
        | unsuspending.to(execute)
        | stopping.to(stopped)
        | aborting.to(aborted)
        | clearing.to(stopped)
        | resetting.to(idle)
    )
    program_complete = execute.to(completing)

    @property
    def state_id(self) -> str:
        return self.current_state.id

    def accepts(self, event: str) -> bool:
        """True when ``event`` has a transition from the current state."""
        for transition in self.current_state.transitions:
            if any(getattr(ev, "id", str(ev)) == event for ev in transition.events):
                return True
        return False


ACTING_STATES = ("starting", "completing", "holding", "unholding", "suspending",
                 "unsuspending", "stopping", "aborting", "clearing", "resetting")
# Unit states in which the program's actions run.
EXECUTING_STATES = ("execute",)
# Unit states in which the runner does not need the control lease.
LEASE_FREE_STATES = ("idle", "stopped", "aborted", "complete")
