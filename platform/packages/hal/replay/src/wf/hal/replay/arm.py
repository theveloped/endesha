"""ReplayArmBackend: an arm whose source stream is a recording (RFC step 6).

Replays the recorded ``arm/{rid}/state/joints`` (+ ``state/io``) into the active
namespace via the shared ``ArmCore`` — joints feed ``core.publish_motion`` so
the core recomputes flange/tcp, re-stamped to ``now_ns()`` (fresh, like the
arm_sim mirror) so downstream never sees it as stale. A 1 Hz synthetic status
heartbeat keeps the UI's liveliness rule satisfied for any recording. Motion is
blocked (``motion_block_reason="replay"``): you cannot command a recording.

Run: ``python -m wf.hal.replay.arm --cell <realized cell> --resource r1``.
"""

from __future__ import annotations

import argparse
import os
import threading

from wf.contracts.arm.messages import IoState, JointState
from wf.core.codec import decode
from wf.core.log import get_logger
from wf.core.session import declare_alive, open_session
from wf.core.time import CLOCK_HOST, now_ns
from wf.hal.arm_core import ArmBackend, ArmCore
from wf.hal.aubo_i10 import BUNDLED_URDF

from .playback import LoopPlayer, read_resource_params

_log = get_logger("wf.hal.replay.arm")

_RUCKIG_DEFAULTS = {"vmax": [1.5] * 6, "amax": [3.0] * 6, "jmax": [20.0] * 6}


class ReplayArmBackend(ArmBackend):
    def __init__(self, params: dict):
        self.params = params
        self.core = None
        self._recording = params.get("recording")
        self._label = os.path.basename(self._recording) if self._recording else "?"
        self._lock = threading.Lock()
        self._latest_q: list[float] | None = None
        self._stop = threading.Event()
        self._player: LoopPlayer | None = None

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self, core) -> None:
        self.core = core
        self._player = LoopPlayer(self._recording, self._match, self._on_record)
        self._player.start()
        threading.Thread(
            target=self._status_loop, name="replay-arm-status", daemon=True
        ).start()
        _log.info("replay arm up: rid=%s recording=%s", core.rid, self._label)

    def shutdown(self) -> None:
        self._stop.set()
        if self._player is not None:
            self._player.stop()

    # ── playback ─────────────────────────────────────────────────────────

    def _match(self, topic: str) -> bool:
        rid = self.core.rid
        return topic.endswith(f"/arm/{rid}/state/joints") or topic.endswith(
            f"/arm/{rid}/state/io"
        )

    def _on_record(self, record) -> None:
        if record.topic.endswith("/state/joints"):
            js = JointState.from_wire(decode(record.payload))
            with self._lock:
                self._latest_q = list(js.q)
            # Re-stamp fresh; the core recomputes flange/tcp from q.
            self.core.publish_motion(
                list(js.q), list(js.qd), list(js.tau), now_ns(), CLOCK_HOST
            )
        elif record.topic.endswith("/state/io"):
            io = IoState.from_wire(decode(record.payload))
            self.core.publish_io(io.di, io.do_, io.ai, io.ao)

    def _status_loop(self) -> None:
        while not self._stop.wait(1.0):
            err = self._player.error if self._player is not None else "no recording"
            self.core.publish_status(
                mode=f"Replay({self._label})",
                servo_on=True,
                estop=False,
                protective_stop=False,
                speed_scale=1.0,
                error=err,
            )

    # ── core seam (motion is blocked — you cannot command a recording) ──

    def latest_q(self) -> list[float] | None:
        with self._lock:
            return None if self._latest_q is None else list(self._latest_q)

    def motion_block_reason(self, *, for_goal: bool) -> str | None:
        return "replay"

    def run_path(self, handle, trajectory, wp_idx, targets, snapshot) -> None:
        # Goals are rejected at accept (motion_block_reason); never invoked.
        handle.fail(error="replay")

    def set_do(self, bank: str, pin: int, value: int) -> None:
        raise RuntimeError("arm in replay (source is a recording)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="wf.hal.replay.arm", description=__doc__)
    parser.add_argument("--cell", required=True, help="path to cell.yaml")
    parser.add_argument("--resource", default="r1", help="resource id (default r1)")
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "cell"),
        help="namespace (default env WF_REALM or 'cell')",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    params = read_resource_params(args.cell, args.resource)
    params.setdefault("servo_cycle_s", 0.005)
    params.setdefault("joint_limit_margin_rad", 0.01)
    params.setdefault("ruckig_defaults", _RUCKIG_DEFAULTS)
    params["urdf"] = params.get("urdf") or BUNDLED_URDF
    backend = ReplayArmBackend(params)

    session = open_session(args.zenoh_config)
    token = declare_alive(session, args.realm, "arm", args.resource)
    core = ArmCore(
        session, args.realm, args.resource, params, backend, driver_version="replay"
    )
    try:
        core.start()
        core.run_forever()
    finally:
        del token
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
