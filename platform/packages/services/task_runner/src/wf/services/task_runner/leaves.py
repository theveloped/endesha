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
    IoState,
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


class LeafError(Exception):
    """A leaf operation failed; the statechart routes this to ``failed``."""


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
        """Read named pose ``config/poses/{name}`` and execute a movej to its ``q``."""
        if self._abort.is_set():
            raise LeafError("aborted")
        reply = self._query(config_keys.pose(pose_name), {})
        if reply is None:
            raise LeafError(f"unknown_pose:{pose_name}")
        q = [float(v) for v in reply["q"]]
        self.acquire_lease()
        client = ActionClient(
            self.session, arm_keys.action_prefix(self.realm, self.rid), "execute_path"
        )
        goal_msg = ExecutePathGoal(
            waypoints=[Waypoint(type="movej", target={"q": q})],
            client_id=self.client_id,
        )
        try:
            self._goal = client.send(goal_msg.to_wire())
        except ActionRejected as exc:
            raise LeafError(f"motion_rejected:{exc.reason}") from exc
        result = self._goal.result(timeout_s=120.0)
        self._goal = None
        if result.get("state") != "succeeded":
            raise LeafError(f"motion_failed:{result.get('state')}")

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
