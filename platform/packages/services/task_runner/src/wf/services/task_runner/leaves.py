"""Leaves: the only bus-touching code the statechart drives (design: task_runner).

The statechart callbacks call ``Leaves.*`` and mutate ``self.context``; nothing
else touches zenoh. A :class:`Leaves` holds the session + ids and the
subscribe-latest caches (pipeline ``result``, arm ``state/io``) the leaves poll.

Leaf failures raise; the statechart routes them to its ``failed`` state.
"""

from __future__ import annotations

import threading
import time

from wf.contracts.arm import keys as arm_keys
from wf.contracts.arm.messages import (
    AcquireControl,
    ControlAck,
    ExecutePathGoal,
    Freedom,
    IoState,
    Pose,
    SetDo,
    Waypoint,
)
from wf.contracts.camera2d import keys as cam_keys
from wf.contracts.camera2d.messages import FrameSpec, GrabReply
from wf.contracts.vision import keys as vision_keys
from wf.core.action import ActionClient, ActionRejected
from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.services.config import keys as config_keys

_log = get_logger("wf.services.task_runner.leaves")

_GRAB_TIMEOUT_S = 15.0
_RESULT_SETTLE_S = 2.0
_IO_POLL_S = 0.05

MOTION_TYPES = ("movej", "movel")


class LeafError(Exception):
    """A leaf operation failed; the statechart routes this to ``failed``."""


def build_move_waypoint(
    *,
    motion: str = "movej",
    q=None,
    pose: Pose | dict | None = None,
    free: Freedom | dict | None = None,
    speed: float | None = None,
    accel: float | None = None,
) -> Waypoint:
    """Assemble a single ``execute_path`` :class:`Waypoint` from graph params.

    Exactly one of ``q`` (joint target) or ``pose`` (Cartesian target for the
    active TCP) must be given. ``free`` (a :class:`Freedom` or its dict form)
    leaves one goal DOF ranged for the loose-goal solver — valid only with a
    ``pose`` target. ``motion`` is ``movej`` (IK + joint interpolation) or
    ``movel`` (straight Cartesian line). Pure: no bus, unit-tested directly.
    """
    if motion not in MOTION_TYPES:
        raise LeafError(f"bad_move:motion must be one of {MOTION_TYPES}")
    if (q is None) == (pose is None):
        raise LeafError("bad_move:give exactly one of q or pose")
    if q is not None:
        if free is not None:
            raise LeafError("bad_move:free requires a pose target")
        target: dict = {"q": [float(v) for v in q]}
    else:
        target = {"pose": pose.to_wire() if isinstance(pose, Pose) else dict(pose)}
        if free is not None:
            target["free"] = free.to_wire() if isinstance(free, Freedom) else dict(free)
    return Waypoint(type=motion, target=target, speed=speed, accel=accel)


class Leaves:
    def __init__(
        self,
        session,
        realm: str,
        *,
        rid: str,
        cid: str,
        pipeline: str,
        client_id: str,
    ) -> None:
        self.session = session
        self.realm = realm
        self.rid = rid
        self.cid = cid
        self.pipeline = pipeline
        self.client_id = client_id
        self._abort = threading.Event()

        # subscribe-latest caches
        self._lock = threading.Lock()
        self._latest_result: dict | None = None
        self._latest_io: IoState | None = None
        self._result_sub = session.declare_subscriber(
            vision_keys.result(realm, pipeline), self._on_result
        )
        self._io_sub = session.declare_subscriber(
            arm_keys.state_io(realm, rid), self._on_io
        )

    # ── lifecycle ────────────────────────────────────────────────────────

    def abort(self) -> None:
        self._abort.set()

    def aborted(self) -> bool:
        return self._abort.is_set()

    def close(self) -> None:
        for sub in (self._result_sub, self._io_sub):
            try:
                sub.undeclare()
            except Exception:
                pass

    # ── cache callbacks ──────────────────────────────────────────────────

    def _on_result(self, sample) -> None:
        try:
            with self._lock:
                self._latest_result = decode(sample.payload)
        except Exception:
            _log.debug("malformed vision result, skipping", exc_info=True)

    def _on_io(self, sample) -> None:
        try:
            io = IoState.from_wire(decode(sample.payload))
            with self._lock:
                self._latest_io = io
        except Exception:
            _log.debug("malformed io state, skipping", exc_info=True)

    # ── lease ────────────────────────────────────────────────────────────

    def acquire_lease(self) -> None:
        """Acquire/renew the control lease under our ``client_id``; raise on denial."""
        reply = self._query(
            arm_keys.cmd_acquire_control(self.realm, self.rid),
            AcquireControl(client_id=self.client_id, user="task_runner").to_wire(),
        )
        if reply is None:
            raise LeafError("lease:no_reply")
        ack = ControlAck.from_wire(reply)
        if not ack.ok:
            raise LeafError(f"lease:{ack.error or 'denied'}")

    def release_lease(self) -> None:
        try:
            self._query(
                arm_keys.cmd_release_control(self.realm, self.rid),
                {"client_id": self.client_id},
            )
        except Exception:
            _log.debug("lease release failed", exc_info=True)

    # ── motion ───────────────────────────────────────────────────────────

    def move_to(self, pose_name: str) -> None:
        """Read named pose ``config/poses/{name}`` and execute a movej to its ``q``.

        The legacy statechart's mover; a thin wrapper over :meth:`move`.
        """
        self.move(motion="movej", pose_name=pose_name)

    def move(
        self,
        *,
        motion: str = "movej",
        pose_name: str | None = None,
        pose: Pose | dict | None = None,
        frame: str | None = None,
        q=None,
        free: Freedom | dict | None = None,
        speed: float | None = None,
        accel: float | None = None,
    ) -> None:
        """Execute a single move to a joint / pose / frame / named-pose target.

        Target forms (first non-None wins): ``q`` (joints), ``pose``
        (``{frame,xyz,quat}`` Cartesian for the active TCP), ``frame`` (that
        frame's origin, identity orientation), or ``pose_name`` (a
        ``config/poses/{name}`` joint pose). ``motion`` is ``movej``/``movel``;
        ``free`` ranges one goal DOF (pose targets only).
        """
        if self._abort.is_set():
            raise LeafError("aborted")
        rq, rpose = self._resolve_move_target(pose_name, pose, frame, q)
        freedom = Freedom.from_wire(free) if isinstance(free, dict) else free
        wp = build_move_waypoint(
            motion=motion, q=rq, pose=rpose, free=freedom, speed=speed, accel=accel
        )
        self._execute_waypoints([wp])

    def _resolve_move_target(self, pose_name, pose, frame, q):
        """Resolve the four target forms to ``(q, pose)`` for the waypoint builder."""
        if q is not None:
            return list(q), None
        if pose is not None:
            return None, pose
        if frame is not None:
            return None, Pose(frame=frame, xyz=[0.0, 0.0, 0.0], quat=[0.0, 0.0, 0.0, 1.0])
        if pose_name is not None:
            reply = self._query(config_keys.pose(pose_name), {})
            if reply is None or "q" not in reply:
                raise LeafError(f"unknown_pose:{pose_name}")
            return [float(v) for v in reply["q"]], None
        raise LeafError("bad_move:no target (q/pose/frame/pose_name)")

    def _execute_waypoints(self, waypoints: list[Waypoint]) -> None:
        self.acquire_lease()
        client = ActionClient(
            self.session, arm_keys.action_prefix(self.realm, self.rid), "execute_path"
        )
        goal_msg = ExecutePathGoal(waypoints=waypoints, client_id=self.client_id)
        try:
            self._goal = client.send(goal_msg.to_wire())
        except ActionRejected as exc:
            raise LeafError(f"motion_rejected:{exc.reason}") from exc
        result = self._goal.result(timeout_s=120.0)
        self._goal = None
        if result.get("state") != "succeeded":
            raise LeafError(f"motion_failed:{result.get('state')}")

    def grip(
        self, *, action: str | None = None, value: bool | None = None, pin: int = 0
    ) -> None:
        """Drive a gripper via the arm's **tool** DO bank.

        ``action`` ``"close"``/``"open"`` maps to DO high/low; an explicit
        ``value`` overrides when a gripper wires the opposite polarity.
        """
        if self._abort.is_set():
            raise LeafError("aborted")
        if value is None:
            if action not in ("open", "close"):
                raise LeafError("bad_grip:action must be 'open' or 'close'")
            value = action == "close"
        self._set_tool_do(int(pin), bool(value))

    def _set_tool_do(self, pin: int, value: bool) -> None:
        reply = self._query(
            arm_keys.cmd_set_do(self.realm, self.rid),
            SetDo("tool", pin, value).to_wire(),
        )
        if reply is None or not reply.get("ok"):
            raise LeafError(f"grip:{None if reply is None else reply.get('error')}")

    def wait_di(self, pin: int, *, timeout_s: float = 5.0, level: bool = True) -> dict:
        """Block until standard DI ``pin`` reaches ``level`` or ``timeout_s`` elapses."""
        start = time.monotonic()
        want = bool(level)
        while True:
            if self._abort.is_set():
                raise LeafError("aborted")
            with self._lock:
                io = self._latest_io
            if io is not None and bool((io.di >> pin) & 1) == want:
                return {"tripped": True, "elapsed_s": time.monotonic() - start}
            if time.monotonic() - start >= timeout_s:
                return {"tripped": False, "elapsed_s": time.monotonic() - start}
            time.sleep(_IO_POLL_S)

    def cancel_motion(self) -> None:
        goal = getattr(self, "_goal", None)
        if goal is not None:
            try:
                goal.cancel()
            except Exception:
                _log.debug("goal cancel failed", exc_info=True)

    # ── vision ───────────────────────────────────────────────────────────

    def enable_pipeline(self, fmt_or_false) -> None:
        """Toggle the detection pipeline on (``fmt`` str / True) or off (False)."""
        enabled = bool(fmt_or_false)
        fmt = fmt_or_false if isinstance(fmt_or_false, str) else None
        reply = self._query(
            vision_keys.cmd_enable(self.realm, self.pipeline),
            {"enabled": enabled, "fmt": fmt},
        )
        if reply is None or not reply.get("ok"):
            raise LeafError("pipeline_enable_failed")

    def read_results(self) -> list[dict]:
        """Grab one frame at the settled pose, return the pipeline's fresh detections.

        Records the cached result ``seq``, issues ONE ``cmd/grab`` (grab shares
        the camera ``image`` topic the enabled pipeline subscribes to), then
        polls the cache for a result whose ``seq`` advanced past the recorded
        one and returns its ``detections`` (``[]`` on timeout).
        """
        if self._abort.is_set():
            raise LeafError("aborted")
        with self._lock:
            prev = self._latest_result
        prev_seq = prev.get("seq") if prev else None

        reply = self._query(
            cam_keys.cmd_grab(self.realm, self.cid),
            FrameSpec(encoding="jpeg", quality=90).to_wire(),
            timeout_s=_GRAB_TIMEOUT_S,
        )
        if reply is None:
            raise LeafError("grab:no_reply")
        grab = GrabReply.from_wire(reply)
        if not grab.ok:
            raise LeafError(f"grab:{grab.error or 'failed'}")

        deadline = time.monotonic() + _RESULT_SETTLE_S
        while time.monotonic() < deadline:
            with self._lock:
                cur = self._latest_result
            if cur is not None and cur.get("seq") != prev_seq:
                return list(cur.get("detections", []))
            time.sleep(0.02)
        return []

    # ── conveyor ─────────────────────────────────────────────────────────

    def run_conveyor(self, do_pin: int, di_pin: int, timeout_s: float) -> dict:
        """Hold a DO high until the watched DI goes high OR ``timeout_s`` elapses.

        Works identically on real IO (DI trips) and in sim (DI is static 0 ->
        timeout fallback). Returns ``{tripped_by, elapsed_s}``.
        """
        self._set_do(do_pin, True)
        start = time.monotonic()
        tripped = False
        try:
            while True:
                if self._abort.is_set():
                    break
                with self._lock:
                    io = self._latest_io
                if io is not None and (io.di >> di_pin) & 1:
                    tripped = True
                    break
                if time.monotonic() - start >= timeout_s:
                    break
                time.sleep(_IO_POLL_S)
        finally:
            self._set_do(do_pin, False)
        return {
            "tripped_by": "di" if tripped else "timeout",
            "elapsed_s": time.monotonic() - start,
        }

    def _set_do(self, pin: int, value: bool) -> None:
        reply = self._query(
            arm_keys.cmd_set_do(self.realm, self.rid),
            SetDo("standard", pin, value).to_wire(),
        )
        if reply is None or not reply.get("ok"):
            raise LeafError(f"set_do:{None if reply is None else reply.get('error')}")

    # ── bus helper ───────────────────────────────────────────────────────

    def _query(self, key: str, payload: dict, *, timeout_s: float = 5.0):
        replies = self.session.get(key, payload=encode(payload), timeout=timeout_s)
        for reply in replies:
            sample = reply.ok
            if sample is not None:
                return decode(sample.payload)
        return None
