"""ReplayCameraBackend: a camera whose source is a recording (RFC step 6).

Republishes the recorded ``camera2d/{cid}/image`` frames into the active
namespace via the shared ``Camera2dCore``: each recorded frame's bytes go out
with a fresh ``seq``/``t_capture`` while preserving the recorded eye-in-hand
pose for the camera frustum and scene placement. Grab is rejected because the
source is a recording; the frame stream flows automatically.

Run: ``python -m wf.hal.replay.camera --cell <realized cell> --resource cam0``.
"""

from __future__ import annotations

import argparse
import os

from wf.contracts.camera2d.messages import FrameHeader
from wf.core.codec import decode
from wf.core.log import get_logger
from wf.core.session import declare_alive, open_session
from wf.hal.camera2d_core import Camera2dBackend, Camera2dCore, CapturedFrame

from .playback import LoopPlayer, read_resource_params

_log = get_logger("wf.hal.replay.camera")

_STREAM_DEFAULTS = {"rate_hz": 15.0, "scale": 0.25, "encoding": "jpeg", "quality": 75}
_GRAB_DEFAULTS = {"scale": 1.0, "encoding": "jpeg", "quality": 90}


class ReplayCameraBackend(Camera2dBackend):
    def __init__(self, params: dict):
        self.params = params
        self.core = None
        self._recording = params.get("recording")
        self._label = os.path.basename(self._recording) if self._recording else "?"
        self._last_exposure: float | None = None
        self._last_gain: float | None = None
        self._player: LoopPlayer | None = None

    def start(self, core) -> None:
        self.core = core
        self._player = LoopPlayer(self._recording, self._match, self._on_record)
        self._player.start()
        _log.info("replay camera up: cid=%s recording=%s", core.cid, self._label)

    def shutdown(self) -> None:
        if self._player is not None:
            self._player.stop()

    def _match(self, topic: str) -> bool:
        return topic.endswith(f"/camera2d/{self.core.cid}/image")

    def _on_record(self, record) -> None:
        if record.attachment is None:
            return
        hdr = FrameHeader.from_wire(decode(record.attachment))
        self._last_exposure = hdr.exposure_us
        self._last_gain = hdr.gain_db
        # Fresh seq/t_capture (re-stamped by the core), recorded pose preserved.
        self.core.publish_frame(
            CapturedFrame(
                data=record.payload,
                w=hdr.w,
                h=hdr.h,
                encoding=hdr.encoding,
                hw_ts_ns=0,
                exposure_us=hdr.exposure_us,
                gain_db=hdr.gain_db,
                pose=hdr.pose,
            )
        )

    # ── core seam (no live acquisition — the frames flow from the file) ──

    def grab(self, spec) -> CapturedFrame:
        raise RuntimeError("camera in replay (source is a recording)")

    def start_stream(self, spec) -> None:
        pass  # frames already flow from the recording

    def stop_stream(self) -> None:
        pass

    def active_stream(self):
        return None

    def status(self) -> dict:
        err = self._player.error if self._player is not None else "no recording"
        return {
            "connected": err is None,
            "exposure_us": self._last_exposure,
            "gain_db": self._last_gain,
            "error": err,
        }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="wf.hal.replay.camera", description=__doc__)
    parser.add_argument("--cell", required=True, help="path to cell.yaml")
    parser.add_argument("--resource", default="cam0", help="resource id (default cam0)")
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "cell"),
        help="namespace (default env WF_REALM or 'cell')",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    params = read_resource_params(args.cell, args.resource)
    params.setdefault("mount_arm", "r1")
    params.setdefault("mount_xyz", [0.0, 0.0, 0.05])
    params.setdefault("mount_rpy_deg", [0.0, 0.0, 0.0])
    params.setdefault("stream_defaults", dict(_STREAM_DEFAULTS))
    params.setdefault("grab_defaults", dict(_GRAB_DEFAULTS))
    backend = ReplayCameraBackend(params)

    session = open_session(args.zenoh_config)
    token = declare_alive(session, args.realm, "camera2d", args.resource)
    core = Camera2dCore(session, args.realm, args.resource, params, backend)
    try:
        core.start()
        core.run_forever()
    finally:
        del token
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
