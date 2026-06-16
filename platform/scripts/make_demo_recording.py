"""Build a hardware-free demo recording for UI replay verification.

Writes ``deploy/recordings/demo.mcap``: 30 s of synthetic ``live/arm/r1``
state at a real wall-clock epoch (ns > 2^53, exercising the UI BigInt path),
with three marks. Replay it with::

    uv run python -m wf.services.recording.replayer deploy/recordings/demo.mcap

Run: ``uv run python scripts/make_demo_recording.py``.
"""

from __future__ import annotations

import math
import os

import cbor2
import cv2
import numpy as np

from wf.core.codec import encode
from wf.core.time import now_ns
from wf.services.recording.sink import McapSink

OUT_PATH = os.path.join("deploy", "recordings", "demo.mcap")

# HOME_DEG pose in radians; joints sweep +/-0.4 rad around it.
HOME_RAD = [0.0, -0.5236, 2.0944, -0.6981, 1.5708, 0.0]


def main() -> None:
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    t0 = now_ns()  # real epoch: must exceed 2^53 to exercise BigInt decoding
    sink = McapSink(OUT_PATH, "live")

    # 30 s of joints @ 100 Hz: smooth visible sweep for the twin.
    for k in range(3000):
        t = t0 + k * 10_000_000
        q = [
            HOME_RAD[i] + 0.4 * math.sin(2 * math.pi * 0.1 * k / 100 + i)
            for i in range(6)
        ]
        payload = cbor2.dumps(
            {
                "t": t,
                "q": q,
                "qd": [0.0] * 6,
                "tau": [0.0] * 6,
                "clock_domain": "host",
            }
        )
        sink.write("live/arm/r1/state/joints", payload, None, t)

    # 30 s of io @ 2 Hz: walking DI/DO lamps make replay motion obvious.
    for k in range(60):
        t = t0 + k * 500_000_000
        payload = cbor2.dumps(
            {
                "t": t,
                "di": 1 << (k % 16),
                "do": 1 << (15 - k % 16),
                "ai": [4.0 + 0.5 * math.sin(k / 4), 0.0],
                "ao": [5.0, 0.0],
            }
        )
        sink.write("live/arm/r1/state/io", payload, None, t)

    # 30 s of status @ 1 Hz.
    for k in range(30):
        t = t0 + k * 1_000_000_000
        payload = cbor2.dumps(
            {
                "t": t,
                "mode": "Replay-Demo",
                "servo_on": True,
                "estop": False,
                "protective_stop": False,
                "speed_scale": 0.3,
                "active_tcp": "flange",
                "error": None,
                "state_rate_hz": 100.0,
            }
        )
        sink.write("live/arm/r1/state/status", payload, None, t)

    # 30 s of camera frames @ 5 Hz: a white square orbiting the center with
    # a frame counter — replay scrubbing is visually obvious (same
    # philosophy as the walking IO lamps). Header bytes via wf.core.codec
    # encode() so they match driver output exactly.
    gradient = np.tile(
        np.linspace(40, 120, 612, dtype=np.uint8), (512, 1)
    )
    for k in range(150):
        t = t0 + k * 200_000_000
        img = cv2.cvtColor(gradient, cv2.COLOR_GRAY2BGR)
        cx = int(306 + 200 * math.cos(2 * math.pi * k / 150))
        cy = int(256 + 200 * math.sin(2 * math.pi * k / 150))
        cv2.rectangle(img, (cx - 30, cy - 30), (cx + 30, cy + 30), (255, 255, 255), -1)
        cv2.putText(
            img, f"{k:03d}", (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2
        )
        _ok, jpeg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 75])
        attachment = encode(
            {
                "t_capture": t,
                "frame_id": "camera2d/cam0/optical",
                "w": 612,
                "h": 512,
                "encoding": "jpeg",
                "exposure_us": 5000.0,
                "gain_db": 0.0,
                "seq": k,
                "clock_domain": "host",
            }
        )
        sink.write("live/camera2d/cam0/image", jpeg.tobytes(), attachment, t)

    # 30 s of camera status @ 1 Hz.
    for k in range(30):
        t = t0 + k * 1_000_000_000
        payload = cbor2.dumps(
            {
                "t": t,
                "connected": True,
                "streaming": True,
                "stream": {
                    "rate_hz": 5.0,
                    "scale": 0.25,
                    "roi": None,
                    "encoding": "jpeg",
                    "quality": 75,
                },
                "exposure_us": 5000.0,
                "gain_db": 0.0,
                "achieved_rate_hz": 5.0,
                "error": None,
            }
        )
        sink.write("live/camera2d/cam0/state/status", payload, None, t)

    sink.write_mark("start", t0)
    sink.write_mark("mid", t0 + 15_000_000_000)
    sink.write_mark("end", t0 + 29_000_000_000)
    sink.close()

    print(f"wrote {OUT_PATH} ({sink.message_count} messages)")
    print(
        "replay it: uv run python -m wf.services.recording.replayer "
        f"{OUT_PATH} --session demo --start-paused"
    )


if __name__ == "__main__":
    main()
