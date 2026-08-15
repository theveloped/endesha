"""The ``Program`` base class (program-layer RFC §3.2).

Author a program as a ``StateChart`` subclass::

    class PickAndPlace(Program):
        roles = {"arm": "arm", "io": "dio"}
        params = {"cycles": 10}
        triggers = [on_channel("io", "part_present", edge="rising", event="part_arrived")]

        waiting = State(initial=True)
        picking = State()
        done = State(final=True)

        part_arrived = waiting.to(picking)
        picked = picking.to(waiting, unless="last_cycle") | picking.to(done, cond="last_cycle")

        def run_picking(self, ctx):          # the state's ACTION, on a worker thread
            self.m.arm.move_j("pick_above")
            self.m.io.set("gripper", True)
            self.emit("picked")

Semantics (RFC §3.3):

- ``run_<state>(self, ctx)`` is the state's action. It starts when the state
  is entered while the unit executes, runs on its own thread, and is
  **cancelled when the state is left** (Hold/Stop/Abort included) — blocking
  proxy calls raise :class:`ActionCancelled`; long loops call ``ctx.check()``.
  A state without ``run_`` is passive (waits for events).
- Transitions are non-blocking: an event is handled immediately even if the
  action is still running (it gets cancelled).
- ``self.emit(event, **data)`` queues an event to the runner's driver thread
  (never call ``send`` from an action thread).
- ``self.p`` are the params (defaults overridden at load); ``self.m`` the
  bound roles (``self.m.arm``, ``self.m.io``, …).
- Reaching a ``final`` state completes the unit.
- Optional hooks (called on the driver thread): ``on_hold()``, ``on_resume()``,
  ``on_abort(reason)``, ``on_stop()``.

The runner (``wf.services.program_runner``) owns the PackML unit machine,
threads, lease and bus; a program never sees them.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol

from statemachine import State, StateChart

from .machine import Roles
from .triggers import Trigger


class ProgramRuntime(Protocol):
    """What a Program needs from its host (implemented by the runner and by
    test doubles)."""

    def program_event(self, event: str, data: dict) -> None: ...
    def state_entered(self, program: "Program", state: State, event: str | None) -> None: ...
    def state_exited(self, program: "Program", state: State, event: str | None) -> None: ...
    def program_transition(self, program: "Program", source: str | None, target: str, event: str | None) -> None: ...
    def log(self, message: str) -> None: ...


class Program(StateChart):
    #: Catalog name; defaults to the module file stem when None. (Not ``name``:
    #: python-statemachine reserves that for the class name.)
    program_name: str | None = None
    #: role -> contract; bound to device ids at load.
    roles: dict[str, str] = {}
    #: default params; overridable at load, available as ``self.p``.
    params: dict = {}
    #: declarative event sources evaluated by the runner.
    triggers: list[Trigger] = []

    def __init__(self, roles: Roles, params: dict, runtime: ProgramRuntime):
        self.m = roles
        self.p = dict(params)
        self._runtime = runtime
        # StateChart.__init__ enters the initial state -> on_enter_state fires;
        # the runtime decides whether an action may start (unit must execute).
        super().__init__()

    # ── program-facing API ───────────────────────────────────────────────

    def emit(self, event: str, **data: Any) -> None:
        """Queue ``event`` for the driver thread (safe from action threads)."""
        self._runtime.program_event(event, data)

    def log(self, message: str) -> None:
        self._runtime.log(message)

    def action_for(self, state_id: str) -> Callable | None:
        return getattr(self, f"run_{state_id}", None)

    @property
    def active_state_ids(self) -> list[str]:
        return sorted(s.id for s in self.configuration)

    @property
    def is_done(self) -> bool:
        return bool(self.is_terminated)

    # ── generic StateChart listeners -> runtime ──────────────────────────

    def on_enter_state(self, state, event=None, **kwargs) -> None:
        self._runtime.state_entered(self, state, _event_id(event))

    def on_exit_state(self, state, event=None, **kwargs) -> None:
        self._runtime.state_exited(self, state, _event_id(event))

    def on_transition(self, event=None, source=None, target=None, **kwargs) -> None:
        self._runtime.program_transition(
            self,
            None if source is None else getattr(source, "id", str(source)),
            "" if target is None else getattr(target, "id", str(target)),
            _event_id(event),
        )

    # ── optional hooks (override in subclasses) ──────────────────────────

    def on_hold(self) -> None: ...
    def on_resume(self) -> None: ...
    def on_abort(self, reason: str) -> None: ...
    def on_stop(self) -> None: ...

    # ── class-level introspection for the catalog ────────────────────────

    @classmethod
    def describe(cls) -> dict:
        return {
            "roles": dict(cls.roles),
            "params": dict(cls.params),
            "doc": (cls.__doc__ or "").strip(),
            "states": [s.id for s in cls.states],
            "events": sorted({e.id for e in cls.events}),
        }


def _event_id(event) -> str | None:
    if event is None:
        return None
    return getattr(event, "id", None) or getattr(event, "name", None) or str(event)
