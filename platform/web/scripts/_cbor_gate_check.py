"""Decode the TS-emitted CBOR cases and assert TYPE fidelity against the
camera2d contract from_wire. Run from platform/: pixi run python web/scripts/_cbor_gate_check.py
"""
import json
import sys
from pathlib import Path

import cbor2

from wf.contracts.camera2d.messages import (
    Ack,
    CameraStatus,
    FrameHeader,
    GrabReply,
    StreamParams,
)

OUT = Path(__file__).parent / "_cbor_out"
manifest = json.loads((OUT / "manifest.json").read_text())
fails = []


def check(name, cond, msg):
    if not cond:
        fails.append(f"{name}: {msg}")


def load(name):
    return cbor2.loads((OUT / f"{name}.cbor").read_bytes())


# ack
d = load("ack")
a = Ack.from_wire(d)
check("ack", a.ok is True, f"ok not True singleton: {a.ok!r}")
check("ack", a.error is None, f"error not None: {a.error!r}")
d = load("ack_err")
a = Ack.from_wire(d)
check("ack_err", a.ok is False and a.error == "boom", f"{a!r}")

# header WITH pose
d = load("header_pose")
check("header_pose", "pose" in d, "pose key missing when present")
h = FrameHeader.from_wire(d)
check("header_pose", isinstance(h.exposure_us, float), f"exposure_us type {type(h.exposure_us)}")
check("header_pose", isinstance(h.gain_db, float), f"gain_db (0.0) type {type(h.gain_db)} must be float")
check("header_pose", isinstance(h.w, int) and not isinstance(h.w, bool), f"w type {type(h.w)}")
check("header_pose", isinstance(h.t_capture, int), f"t_capture type {type(h.t_capture)}")
check("header_pose", h.t_capture == 1_700_000_000_000_000_000, f"t_capture value {h.t_capture}")
check("header_pose", h.pose is not None, "pose decoded None")
check("header_pose", all(isinstance(x, float) for x in h.pose["xyz"]), f"pose.xyz not all float: {h.pose['xyz']}")
check("header_pose", all(isinstance(x, float) for x in h.pose["quat"]), f"pose.quat not all float: {h.pose['quat']}")
check("header_pose", h.pose["frame"] == "world", f"pose.frame {h.pose['frame']!r}")

# header WITHOUT pose -> key absent
d = load("header_nopose")
check("header_nopose", "pose" not in d, f"pose key PRESENT when None (must be omitted): keys={list(d.keys())}")
h = FrameHeader.from_wire(d)
check("header_nopose", h.pose is None, "pose not None")
check("header_nopose", isinstance(h.gain_db, float) and h.gain_db == 1.5, f"gain_db {h.gain_db!r}")

# stream params (flat)
d = load("stream")
sp = StreamParams.from_wire(d)
check("stream", isinstance(sp.rate_hz, float) and sp.rate_hz == 15.0, f"rate_hz {sp.rate_hz!r}")
check("stream", isinstance(sp.scale, float) and sp.scale == 0.25, f"scale {sp.scale!r}")
check("stream", sp.roi is None, f"roi {sp.roi!r}")
check("stream", isinstance(sp.quality, int) and sp.quality == 75, f"quality {sp.quality!r}")
check("stream", sp.encoding == "jpeg", f"encoding {sp.encoding!r}")

# grab ok -> data is bytes (CBOR byte string), header present
d = load("grab_ok")
g = GrabReply.from_wire(d)
check("grab_ok", g.ok is True, f"ok {g.ok!r}")
check("grab_ok", isinstance(g.data, (bytes, bytearray)), f"data type {type(g.data)} must be bytes")
check("grab_ok", g.data[:2] == b"\xff\xd8", f"data not JPEG SOI: {g.data[:2]!r}")
check("grab_ok", g.header is not None and g.header.seq == 1, f"header {g.header!r}")
# grab err -> all keys present with nulls
d = load("grab_err")
check("grab_err", set(d.keys()) == {"ok", "error", "header", "data"}, f"grab_err keys {set(d.keys())}")
g = GrabReply.from_wire(d)
check("grab_err", g.ok is False and g.error == "camera is streaming" and g.header is None and g.data is None, f"{g!r}")

# status idle -> achieved_rate_hz float even at 0.0; stream null; all keys present
d = load("status_idle")
check("status_idle", set(d.keys()) == {"t", "connected", "streaming", "stream", "exposure_us", "gain_db", "achieved_rate_hz", "error"}, f"status keys {set(d.keys())}")
s = CameraStatus.from_wire(d)
check("status_idle", s.connected is True, f"connected {s.connected!r} must be True singleton")
check("status_idle", s.streaming is False, f"streaming {s.streaming!r}")
check("status_idle", isinstance(s.achieved_rate_hz, float), f"achieved_rate_hz (0.0) type {type(s.achieved_rate_hz)} must be float")
check("status_idle", s.stream is None, f"stream {s.stream!r}")
check("status_idle", isinstance(s.exposure_us, float), f"exposure_us type {type(s.exposure_us)}")

# status streaming -> nested StreamParams + roi list of ints
d = load("status_streaming")
s = CameraStatus.from_wire(d)
check("status_streaming", s.streaming is True, "streaming")
check("status_streaming", s.stream is not None and isinstance(s.stream.rate_hz, float), f"nested stream {s.stream!r}")
check("status_streaming", s.stream.roi == [0, 0, 400, 400] and all(isinstance(x, int) for x in s.stream.roi), f"roi {s.stream.roi!r}")
check("status_streaming", isinstance(s.achieved_rate_hz, float) and abs(s.achieved_rate_hz - 14.9) < 1e-9, f"rate {s.achieved_rate_hz!r}")

if fails:
    print(f"FAIL ({len(fails)}):")
    for fmsg in fails:
        print("  -", fmsg)
    sys.exit(1)
print(f"PASS: {len(manifest)} cases, all types/keys correct")
