"""Per-contract device proxies — the ONLY bus-touching code a program drives.

Every blocking call honours the calling action's :class:`ActionContext`
(cancel -> goal cancel + :class:`ActionCancelled`). Proxies speak contract
keys only, so a program runs unchanged against live / sim / replay sources.
Adding a contract later (serial, opcua, http) = adding a proxy class here and
registering it in :data:`PROXIES`.
"""

from __future__ import annotations

import threading
import time
from typing import Callable

from wf.contracts.arm import keys as arm_keys
from wf.contracts.arm.messages import (
    Ack as ArmAck,
    ArmStatus,
    ExecutePathGoal,
    Freedom,
    JointState,
    Pose,
    Waypoint,
)
from wf.contracts.dio import keys as dio_keys
from wf.contracts.dio.messages import Ack as DioAck
from wf.contracts.dio.messages import ChannelsState, ForceChannel, SetChannel
from wf.core.action import ActionClient, ActionRejected
from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.services.config import keys as config_keys

from .context import ActionContext
from .errors import ActionCancelled, ProgramError

_log = get_logger("wf.program.proxies")

MOTION_TYPES = ("movej", "movel")
_POLL_S = 0.05


def _ctx() -> ActionContext | None:
    return ActionContext.current()


def _check() -> None:
    ctx = _ctx()
    if ctx is not None:
        ctx.check()


def _query(session, key: str, payload: dict, timeout_s: float = 5.0) -> dict | None:
    for reply in session.get(key, payload=encode(payload), timeout=timeout_s):
        if reply.ok is not None:
            return decode(reply.ok.payload)
    return None


def build_move_waypoint(
    *,
    motion: str = "movej",
    q=None,
    pose: Pose | dict | None = None,
    free: Freedom | dict | None = None,
    speed: float | None = None,
    accel: float | None = None,
    blend_radius: float = 0.0,
) -> Waypoint:
    """One ``execute_path`` waypoint from a joint OR Cartesian target. Pure."""
    if motion not in MOTION_TYPES:
        raise ProgramError(f"bad_move:motion must be one of {MOTION_TYPES}")
    if (q is None) == (pose is None):
        raise ProgramError("bad_move:give exactly one of q or pose")
    if q is not None:
        if free is not None:
            raise ProgramError("bad_move:free requires a pose target")
        target: dict = {"q": [float(v) for v in q]}
    else:
        target = {"pose": pose.to_wire() if isinstance(pose, Pose) else dict(pose)}
        if free is not None:
            target["free"] = free.to_wire() if isinstance(free, Freedom) else dict(free)
    return Waypoint(type=motion, target=target, speed=speed, accel=accel, blend_radius=blend_radius)


class DeviceProxy:
    contract: str = ""

    def __init__(self, session, realm: str, rid: str, client_id: str):
        self.session = session
        self.realm = realm
        self.rid = rid
        self.client_id = client_id

    def start(self) -> None:  # subscriptions etc.
        pass

    def close(self) -> None:
        pass


# ── arm ────────────────────────────────────────────────────────────────────


class ArmProxy(DeviceProxy):
    """``self.m.arm`` — motion + status of one arm."""

    contract = "arm"

    def __init__(self, session, realm, rid, client_id, *, pose_resolver: Callable[[str], list[float]]):
        super().__init__(session, realm, rid, client_id)
        self._resolve_pose = pose_resolver
        self._lock = threading.Lock()
        self._joints: JointState | None = None
        self._status: ArmStatus | None = None
        self._subs: list = []
        self._client = ActionClient(session, arm_keys.action_prefix(realm, rid), "execute_path")

    def start(self) -> None:
        self._subs = [
            self.session.declare_subscriber(arm_keys.state_joints(self.realm, self.rid), self._on_joints),
            self.session.declare_subscriber(arm_keys.state_status(self.realm, self.rid), self._on_status),
        ]

    def close(self) -> None:
        for s in self._subs:
            try:
                s.undeclare()
            except Exception:
                pass
        self._subs = []

    def _on_joints(self, sample) -> None:
        try:
            js = JointState.from_wire(decode(sample.payload))
        except Exception:
            return
        with self._lock:
            self._joints = js

    def _on_status(self, sample) -> None:
        try:
            st = ArmStatus.from_wire(decode(sample.payload))
        except Exception:
            return
        with self._lock:
            self._status = st

    # ── reads ────────────────────────────────────────────────────────────

    @property
    def q(self) -> list[float] | None:
        with self._lock:
            return None if self._joints is None else list(self._joints.q)

    @property
    def status(self) -> ArmStatus | None:
        with self._lock:
            return self._status

    # ── motion ───────────────────────────────────────────────────────────

    def move_j(self, target=None, *, q=None, pose=None, frame=None, xyz=None, quat=None,
               free=None, speed=None, accel=None, timeout_s: float = 120.0) -> dict:
        return self._move("movej", target, q, pose, frame, xyz, quat, free, speed, accel, timeout_s)

    def move_l(self, target=None, *, q=None, pose=None, frame=None, xyz=None, quat=None,
               free=None, speed=None, accel=None, timeout_s: float = 120.0) -> dict:
        return self._move("movel", target, q, pose, frame, xyz, quat, free, speed, accel, timeout_s)

    def move_path(self, waypoints: list[Waypoint], *, timeout_s: float = 300.0) -> dict:
        """Execute several waypoints as ONE goal (blend radii honoured)."""
        return self._execute(waypoints, timeout_s)

    def _move(self, motion, target, q, pose, frame, xyz, quat, free, speed, accel, timeout_s) -> dict:
        """Target forms: a named pose (``target="pick_above"`` or ``pose_name``),
        joints (``q=[…]``), a Pose/dict (``pose=``), or a frame + optional
        offset (``frame="tray/slot_3", xyz=[…], quat=[…]``)."""
        if isinstance(target, str):
            q = self._resolve_pose(target)
        elif isinstance(target, (list, tuple)) and len(target) == 6:
            q = list(target)
        elif isinstance(target, (Pose, dict)):
            pose = target
        elif target is not None:
            raise ProgramError(f"bad_move:unsupported target {target!r}")
        if frame is not None and pose is None:
            pose = Pose(
                frame=frame,
                xyz=list(xyz) if xyz is not None else [0.0, 0.0, 0.0],
                quat=list(quat) if quat is not None else [0.0, 0.0, 0.0, 1.0],
            )
        freedom = Freedom.from_wire(free) if isinstance(free, dict) else free
        wp = build_move_waypoint(motion=motion, q=q, pose=pose, free=freedom, speed=speed, accel=accel)
        return self._execute([wp], timeout_s)

    def _execute(self, waypoints: list[Waypoint], timeout_s: float) -> dict:
        _check()
        goal_msg = ExecutePathGoal(waypoints=waypoints, client_id=self.client_id)
        try:
            goal = self._client.send(goal_msg.to_wire())
        except ActionRejected as exc:
            raise ProgramError(f"motion_rejected:{exc.reason}") from exc
        except TimeoutError as exc:
            raise ProgramError("motion_rejected:no_reply") from exc
        ctx = _ctx()
        unregister = None
        if ctx is not None:
            unregister = ctx.on_cancel(lambda: self._cancel_goal(goal))
        try:
            deadline = time.monotonic() + timeout_s
            while True:
                try:
                    result = goal.result(timeout_s=0.5)
                    break
                except TimeoutError:
                    if ctx is not None and ctx.cancelled:
                        raise ActionCancelled(ctx.state_id) from None
                    if time.monotonic() >= deadline:
                        self._cancel_goal(goal)
                        raise ProgramError("motion_timeout") from None
        finally:
            if unregister is not None:
                unregister()
        if ctx is not None and ctx.cancelled:
            raise ActionCancelled(ctx.state_id)
        if result.get("state") != "succeeded":
            raise ProgramError(f"motion_failed:{result.get('state')}:{result.get('error')}")
        return result

    @staticmethod
    def _cancel_goal(goal) -> None:
        try:
            goal.cancel(timeout_s=2.0)
        except Exception:
            _log.debug("goal cancel failed", exc_info=True)

    def set_tcp(self, name: str) -> None:
        _check()
        reply = _query(self.session, arm_keys.cmd_set_tcp(self.realm, self.rid), {"name": name})
        if reply is None:
            raise ProgramError("set_tcp:no_reply")
        ack = ArmAck.from_wire(reply)
        if not ack.ok:
            raise ProgramError(f"set_tcp:{ack.error}")

    def stop(self) -> None:
        _query(self.session, arm_keys.cmd_stop(self.realm, self.rid), {})


# ── dio ────────────────────────────────────────────────────────────────────


class DioProxy(DeviceProxy):
    """``self.m.io`` — named channels of one dio device."""

    contract = "dio"

    def __init__(self, session, realm, rid, client_id):
        super().__init__(session, realm, rid, client_id)
        self._lock = threading.Lock()
        self._state: ChannelsState | None = None
        self._changed = threading.Condition(self._lock)
        self._sub = None
        self._watchers: list[Callable[[str, object, object], None]] = []

    def watch(self, callback: Callable[[str, object, object], None]) -> Callable[[], None]:
        """Register ``callback(name, old, new)`` for every channel value change
        (called on the bus thread; keep it cheap). Returns an unregister fn."""
        with self._lock:
            self._watchers.append(callback)

        def unregister() -> None:
            with self._lock:
                try:
                    self._watchers.remove(callback)
                except ValueError:
                    pass

        return unregister

    def start(self) -> None:
        self._sub = self.session.declare_subscriber(
            dio_keys.state_channels(self.realm, self.rid), self._on_state
        )
        # Late joiner: pull once.
        try:
            reply = _query(self.session, dio_keys.state_channels(self.realm, self.rid), {}, timeout_s=1.0)
            if reply is not None:
                with self._lock:
                    if self._state is None:
                        self._state = ChannelsState.from_wire(reply)
                    self._changed.notify_all()
        except Exception:
            pass

    def close(self) -> None:
        if self._sub is not None:
            try:
                self._sub.undeclare()
            except Exception:
                pass
            self._sub = None

    def _on_state(self, sample) -> None:
        try:
            st = ChannelsState.from_wire(decode(sample.payload))
        except Exception:
            return
        with self._lock:
            prev = self._state
            self._state = st
            self._changed.notify_all()
            watchers = list(self._watchers)
        if watchers and prev is not None:
            for name, cv in st.channels.items():
                old = prev.channels.get(name)
                if old is not None and old.value != cv.value:
                    for fn in watchers:
                        try:
                            fn(name, old.value, cv.value)
                        except Exception:
                            _log.debug("dio watcher failed", exc_info=True)

    # ── reads ────────────────────────────────────────────────────────────

    def get(self, name: str):
        with self._lock:
            st = self._state
        if st is None:
            raise ProgramError(f"dio_no_state:{self.rid}")
        cv = st.channels.get(name)
        if cv is None:
            raise ProgramError(f"unknown_channel:{self.rid}.{name}")
        return cv.value

    def snapshot(self) -> dict:
        with self._lock:
            st = self._state
        return {} if st is None else {n: cv.value for n, cv in st.channels.items()}

    def wait(self, name: str, value=True, *, timeout_s: float | None = None) -> bool:
        """Block until channel ``name`` equals ``value`` (or, when ``value`` is
        callable, until ``value(current)`` is true). Returns True when met,
        False on timeout; raises :class:`ActionCancelled` on cancel."""
        ctx = _ctx()
        deadline = None if timeout_s is None else time.monotonic() + timeout_s
        pred = value if callable(value) else (lambda v, want=value: v == want)
        while True:
            if ctx is not None:
                ctx.check()
            with self._lock:
                st = self._state
                cv = None if st is None else st.channels.get(name)
                if st is not None and cv is None:
                    raise ProgramError(f"unknown_channel:{self.rid}.{name}")
                if cv is not None and pred(cv.value):
                    return True
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    return False
                self._changed.wait(timeout=min(_POLL_S * 4, remaining) if remaining is not None else _POLL_S * 4)

    # ── writes ───────────────────────────────────────────────────────────

    def set(self, name: str, value) -> None:
        _check()
        reply = _query(
            self.session,
            dio_keys.cmd_set(self.realm, self.rid),
            SetChannel(self.client_id, name, value).to_wire(),
        )
        if reply is None:
            raise ProgramError(f"dio_set:{self.rid}.{name}:no_reply")
        ack = DioAck.from_wire(reply)
        if not ack.ok:
            raise ProgramError(f"dio_set:{self.rid}.{name}:{ack.error}")

    def force(self, name: str, value) -> None:
        """Override a channel's reported value (``None`` clears). Meant for
        simulation scenarios / tests, not production logic."""
        _check()
        reply = _query(
            self.session,
            dio_keys.cmd_force(self.realm, self.rid),
            ForceChannel(self.client_id, name, value).to_wire(),
        )
        if reply is None:
            raise ProgramError(f"dio_force:{self.rid}.{name}:no_reply")
        ack = DioAck.from_wire(reply)
        if not ack.ok:
            raise ProgramError(f"dio_force:{self.rid}.{name}:{ack.error}")

    def pulse(self, name: str, seconds: float = 0.2) -> None:
        self.set(name, True)
        ctx = _ctx()
        try:
            if ctx is not None:
                ctx.sleep(seconds)
            else:
                time.sleep(seconds)
        finally:
            self.set(name, False)


# ── pose resolution (cell-scoped config store; program-scoped is RFC §3.7) ─


def make_pose_resolver(session, program_name: str | None = None) -> Callable[[str], list[float]]:
    def resolve(name: str) -> list[float]:
        _check()
        candidates = []
        if program_name:
            candidates.append(f"{config_keys.CONFIG_PREFIX}/programs/{program_name}/poses/{name}")
        candidates.append(config_keys.pose(name))
        for key in candidates:
            reply = _query(session, key, {}, timeout_s=3.0)
            if reply is not None and "q" in reply:
                return [float(v) for v in reply["q"]]
        raise ProgramError(f"unknown_pose:{name}")

    return resolve


PROXIES: dict[str, type[DeviceProxy]] = {"arm": ArmProxy, "dio": DioProxy}
