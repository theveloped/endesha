"""WF program SDK (program-layer RFC §3).

A program is a :class:`Program` — a ``python-statemachine`` StateChart whose
states carry *actions* (``run_<state>(self, ctx)`` methods run on a worker
thread) and whose transitions are driven by events from the program itself
(``self.emit``), from device channels (:func:`on_channel` triggers), from the
HMI/bus, or from timers (:func:`after`).

Programs talk to devices only through :class:`Machine` proxies bound by role
(``self.m.arm.move_j(...)``, ``self.m.io.wait("part_present", True)``), so
the same program runs against live, simulated or replayed devices.

Nothing PackML-related is visible here: Hold/Stop/Abort/Reset are unit-level
concerns of the runner (``wf.services.program_runner``).
"""

from statemachine import State

from .context import ActionContext
from .errors import ActionCancelled, ProgramError
from .machine import Machine, Roles
from .program import Program
from .triggers import Trigger, after, on_channel

__all__ = [
    "ActionCancelled",
    "ActionContext",
    "Machine",
    "Program",
    "ProgramError",
    "Roles",
    "State",
    "Trigger",
    "after",
    "on_channel",
]
