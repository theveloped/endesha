"""YAML spec -> a parallel-region :class:`StateChart` (design: task_runner).

Two regions run CONCURRENTLY inside a ``State.Parallel`` ``work``:

- ``inspect``: ``running -> done`` — a worker thread enables the detection
  pipeline, steps the arm through the named poses (draining the freshest
  pipeline ``result`` at each settled pose into ``context["by_pose"]``), then
  disables the pipeline and enqueues ``inspect_done``.
- ``conveyor``: ``running -> stopped`` — a worker thread holds a DO high until
  the watched DI trips or a timeout elapses, records ``context["conveyor"]``,
  and enqueues ``conveyor_done``.

When BOTH regions reach final, ``done_state_work`` fires the JOIN to the
top-level final ``aggregate`` state, whose ``on_enter`` flattens the per-pose
detections into ``context["summary"]`` and decides success vs ``min_count``.

The library's sync engine is single-threaded-driver: the two region workers run
on their own threads but MUST NOT call ``send`` directly (lost-wakeup race).
Instead each enqueues its done-event onto ``self._event_q``; the owning service
pumps that queue on ONE driver thread (see :meth:`pump`). Region transitions
are EVENT-driven (not eventless) so nothing auto-advances at construction.

Leaf exceptions are caught by ``catch_errors_as_events`` and routed via
``error_execution`` to the terminal ``failed`` state.
"""

from __future__ import annotations

import queue
import threading

from statemachine import State, StateChart
from statemachine.state import NestedStateFactory

from wf.core.log import get_logger

from .leaves import LeafError, Leaves

_log = get_logger("wf.services.task_runner.flow")


def _region(initial_id: str, final_id: str, *, done_event: str):
    """Build a 2-state compound region ``initial -> final`` on ``done_event``."""
    running = State(initial=True)
    done = State(final=True)
    transitions = running.to(done)
    return NestedStateFactory(
        "region",
        (State.Compound,),
        {initial_id: running, final_id: done, done_event: transitions},
    )


def build_flow_class(spec: dict) -> type:
    """Construct the StateChart subclass for ``spec`` (validated by ``spec.py``)."""
    poses = spec["poses"]
    vision = spec["vision"]
    conveyor = spec["conveyor"]

    inspect = _region("inspecting", "inspected", done_event="inspect_done")
    conveyor_region = _region("running", "stopped", done_event="conveyor_done")
    work = NestedStateFactory(
        "work",
        (State.Parallel,),
        {"inspect": inspect, "conveyor": conveyor_region},
    )
    aggregate = State(final=True)
    failed = State(final=True)

    def __init__(self, leaves: Leaves):
        self.leaves = leaves
        self.context: dict = {"by_pose": [], "conveyor": None, "summary": None}
        self.error: str | None = None
        self._event_q: queue.Queue = queue.Queue()
        self._threads: list[threading.Thread] = []
        StateChart.__init__(self)

    def _spawn(self, name, target):
        t = threading.Thread(target=target, name=name, daemon=True)
        t.start()
        self._threads.append(t)

    def _inspect_worker(self):
        try:
            self.leaves.enable_pipeline(vision["format"])
            for pose in poses:
                self.leaves.move_to(pose)
                detections = self.leaves.read_results()
                self.context["by_pose"].append(
                    {"pose": pose, "detections": detections}
                )
            self.leaves.enable_pipeline(False)
            self._event_q.put("inspect_done")
        except LeafError as exc:
            self.error = str(exc)
            self._event_q.put(("__error__", str(exc)))

    def _conveyor_worker(self):
        try:
            self.context["conveyor"] = self.leaves.run_conveyor(
                conveyor["do_pin"], conveyor["di_pin"], conveyor["timeout_s"]
            )
            self._event_q.put("conveyor_done")
        except LeafError as exc:
            self.error = str(exc)
            self._event_q.put(("__error__", str(exc)))

    def on_enter_inspecting(self):
        self._spawn("inspect-worker", self._inspect_worker)

    def on_enter_running(self):
        self._spawn("conveyor-worker", self._conveyor_worker)

    def on_enter_aggregate(self):
        codes: list[str] = []
        for entry in self.context["by_pose"]:
            for det in entry["detections"]:
                text = det.get("text")
                if text and text not in codes:
                    codes.append(text)
        self.context["summary"] = {
            "codes": codes,
            "by_pose": self.context["by_pose"],
            "conveyor": self.context["conveyor"],
        }
        self.ok = len(codes) >= vision["min_count"]

    def on_enter_failed(self):
        self.ok = False
        if self.error is None:
            self.error = "failed"
        self.context["summary"] = {
            "codes": [],
            "by_pose": self.context["by_pose"],
            "conveyor": self.context["conveyor"],
        }

    def pump(self, *, poll_s: float = 0.1) -> None:
        """Drive the flow on ONE thread until terminated.

        Drains the worker event queue and applies each event via ``send``; a
        ``("__error__", reason)`` tuple raises into the engine so the
        ``error_execution`` route reaches ``failed``.
        """
        while not self.is_terminated:
            try:
                item = self._event_q.get(timeout=poll_s)
            except queue.Empty:
                continue
            if isinstance(item, tuple) and item and item[0] == "__error__":
                # Raise inside a send so catch_errors_as_events routes to failed.
                self.send("__fail__")
            else:
                self.send(item)

    attrs = {
        "work": work,
        "aggregate": aggregate,
        "failed": failed,
        "done_state_work": work.to(aggregate),
        "error_execution": work.to(failed),
        "__fail__": work.to(failed),
        "catch_errors_as_events": True,
        "ok": False,
        "__init__": __init__,
        "_spawn": _spawn,
        "_inspect_worker": _inspect_worker,
        "_conveyor_worker": _conveyor_worker,
        "on_enter_inspecting": on_enter_inspecting,
        "on_enter_running": on_enter_running,
        "on_enter_aggregate": on_enter_aggregate,
        "on_enter_failed": on_enter_failed,
        "pump": pump,
    }
    return type(f"{spec['name']}_Flow", (StateChart,), attrs)
