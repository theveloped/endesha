"""Per-device replay: playback pacing/loop over a tiny MCAP + backend gates.

No zenoh session and no hardware: the LoopPlayer is driven against a real (but
tiny) recording written with McapSink, and the backends' command-gate behavior
is checked directly.
"""

from __future__ import annotations

import threading
import time

import pytest

from wf.contracts.arm.messages import JointState
from wf.contracts.camera2d.messages import FrameHeader
from wf.core.codec import encode
from wf.hal.replay.arm import ReplayArmBackend
from wf.hal.replay.camera import ReplayCameraBackend
from wf.hal.replay.playback import LoopPlayer, read_resource_params

HOME = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]


@pytest.fixture
def recording(tmp_path):
    """A 3-frame recording: two arm joints (10 ms apart) + one camera image."""
    from wf.services.recording.sink import McapSink

    path = str(tmp_path / "rec.mcap")
    sink = McapSink(path, "live")
    t0 = 1_700_000_000_000_000_000
    for k in range(2):
        js = JointState(
            t=t0 + k * 10_000_000,
            q=[HOME[0] + 0.1 * k] + HOME[1:],
            qd=[0.0] * 6,
            tau=[0.0] * 6,
            clock_domain="host",
        )
        sink.write("live/arm/r1/state/joints", encode(js.to_wire()), None, t0 + k * 10_000_000)
    hdr = FrameHeader(
        t_capture=t0,
        frame_id="camera2d/cam0/optical",
        w=64,
        h=48,
        encoding="jpeg",
        exposure_us=5000.0,
        gain_db=1.5,
        seq=0,
        clock_domain="host",
        pose={"frame": "world", "xyz": [0.1, 0.2, 0.3], "quat": [0, 0, 0, 1]},
    )
    sink.write("live/camera2d/cam0/image", b"\xff\xd8jpegbytes", encode(hdr.to_wire()), t0)
    sink.close()
    return path


# ── LoopPlayer ────────────────────────────────────────────────────────────


def test_loop_player_paces_and_loops(recording):
    got = []
    lock = threading.Lock()

    def on_record(rec):
        with lock:
            got.append(rec.topic)

    player = LoopPlayer(recording, lambda t: t.endswith("/arm/r1/state/joints"), on_record)
    player.start()
    time.sleep(0.3)
    player.stop()
    with lock:
        n = len(got)
    assert player.source_realm == "live"
    assert player.error is None
    # 2 joints records per ~10 ms pass, looping -> well more than one pass.
    assert n > 2


def test_loop_player_no_match_reports_error(recording):
    player = LoopPlayer(recording, lambda t: t.endswith("/arm/rZ/state/joints"), lambda r: None)
    player.start()
    time.sleep(0.2)
    player.stop()
    assert "no matching records" in (player.error or "")


def test_loop_player_missing_recording_errors():
    player = LoopPlayer("does-not-exist.mcap", lambda t: True, lambda r: None)
    player.start()
    time.sleep(0.1)
    player.stop()
    assert "recording unavailable" in (player.error or "")


def test_read_resource_params(tmp_path):
    p = tmp_path / "cell.yaml"
    p.write_text(
        "resources:\n  r1:\n    params: {recording: foo.mcap, servo_cycle_s: 0.005}\n",
        encoding="utf-8",
    )
    assert read_resource_params(str(p), "r1") == {
        "recording": "foo.mcap",
        "servo_cycle_s": 0.005,
    }


# ── backend command gates ───────────────────────────────────────────────────


def test_arm_backend_blocks_motion():
    b = ReplayArmBackend({"recording": None})
    assert b.motion_block_reason(for_goal=True) == "replay"
    assert b.motion_block_reason(for_goal=False) == "replay"
    assert b.latest_q() is None
    with pytest.raises(RuntimeError):
        b.set_do("standard", 0, 1)


def test_camera_backend_rejects_grab():
    b = ReplayCameraBackend({"recording": None})
    with pytest.raises(RuntimeError):
        b.grab(None)
    assert b.active_stream() is None
    st = b.status()
    assert st["connected"] is False and st["error"] == "no recording"
