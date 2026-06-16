"""Conformance tests for the `camera2d` contract. Hardware-facing; bus-only."""

from __future__ import annotations

import time

import pytest

from wf.contracts.camera2d import keys
from wf.contracts.camera2d.messages import (
    Ack,
    CameraStatus,
    ENCODING_BAYER_RG8,
    ENCODING_JPEG,
    FrameSpec,
    GrabReply,
)
from wf.core.codec import decode, encode

from .conftest import collect_frames, collect_samples, first_sample

_JPEG_SOI = b"\xff\xd8"


def _query(session, key: str, payload: dict, timeout_s: float = 5.0) -> dict | None:
    replies = session.get(key, payload=encode(payload), timeout=timeout_s)
    for reply in replies:
        if reply.ok is not None:
            return decode(reply.ok.payload)
    return None


def _query_ack(session, key: str, payload: dict, timeout_s: float = 5.0) -> Ack:
    reply = _query(session, key, payload, timeout_s=timeout_s)
    if reply is None:
        pytest.fail(f"no reply from {key}")
    return Ack.from_wire(reply)


def _grab(session, realm: str, cid: str, spec: dict) -> GrabReply:
    reply = _query(session, keys.cmd_grab(realm, cid), spec, timeout_s=15.0)
    if reply is None:
        pytest.fail("no reply from cmd/grab")
    return GrabReply.from_wire(reply)


def test_alive_token(session, realm, cid):
    replies = session.liveliness().get(keys.alive(realm, cid), timeout=3.0)
    tokens = [reply.ok for reply in replies if reply.ok is not None]
    assert tokens, f"no liveliness token on {keys.alive(realm, cid)}"


def test_status_stream(session, realm, cid):
    status = CameraStatus.from_wire(
        first_sample(session, keys.state_status(realm, cid), timeout_s=3.0)
    )
    assert status.connected is True


def test_grab_roundtrip(session, realm, cid):
    frames: list[tuple[bytes, dict | None]] = []

    def on_sample(s):
        att = s.attachment
        frames.append((s.payload.to_bytes(), None if att is None else decode(att)))

    # Subscriber FIRST: the grab must also appear on the image topic.
    sub = session.declare_subscriber(keys.image(realm, cid), on_sample)
    try:
        grab = _grab(
            session,
            realm,
            cid,
            FrameSpec(encoding=ENCODING_JPEG, quality=90).to_wire(),
        )
        assert grab.ok, grab.error
        assert grab.header is not None
        assert grab.header.w > 0 and grab.header.h > 0
        assert grab.header.encoding == ENCODING_JPEG
        assert grab.data, "empty grab data"
        assert grab.data[:2] == _JPEG_SOI
        assert abs(grab.header.t_capture - time.time_ns()) < 10_000_000_000

        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline:
            if any(
                att is not None and att.get("seq") == grab.header.seq
                for _, att in frames
            ):
                break
            time.sleep(0.05)
        published = [
            payload
            for payload, att in frames
            if att is not None and att.get("seq") == grab.header.seq
        ]
        assert published, "grab frame not published on the image topic"
        assert published[0] == grab.data
    finally:
        sub.undeclare()


def test_grab_spec_variants(session, realm, cid):
    full = _grab(session, realm, cid, {"encoding": ENCODING_JPEG, "quality": 80})
    assert full.ok, full.error

    half = _grab(
        session, realm, cid, {"encoding": ENCODING_JPEG, "quality": 80, "scale": 0.5}
    )
    assert half.ok, half.error
    assert abs(half.header.w - full.header.w / 2) <= 1
    assert abs(half.header.h - full.header.h / 2) <= 1

    bad = _grab(session, realm, cid, {"encoding": ENCODING_BAYER_RG8, "scale": 0.5})
    assert bad.ok is False
    assert bad.error, "expected the FrameSpec validation error string"


def test_stream_lifecycle(session, realm, cid):
    # Pin a deterministic 20 ms exposure: a dark-scene auto-exposure (90 ms
    # observed live) caps the sensor below the requested 10 fps, which would
    # fail the rate check for environmental — not contractual — reasons.
    ack = _query_ack(
        session,
        keys.cmd_configure(realm, cid),
        {"auto_exposure": False, "exposure_us": 20_000.0},
    )
    assert ack.ok, ack.error
    try:
        ack = _query_ack(
            session,
            keys.cmd_stream_start(realm, cid),
            {"rate_hz": 10, "scale": 0.25, "encoding": ENCODING_JPEG},
        )
        assert ack.ok, ack.error
        try:
            frames = collect_frames(
                session, keys.image(realm, cid), duration_s=2.0
            )
            assert len(frames) >= 10, (
                f"expected >= 10 frames in 2 s, got {len(frames)}"
            )
            headers = [att for _, att in frames]
            assert all(att is not None for att in headers), (
                "frame without attachment"
            )
            t_caps = [att["t_capture"] for att in headers]
            seqs = [att["seq"] for att in headers]
            assert all(b > a for a, b in zip(t_caps, t_caps[1:])), (
                "t_capture not strictly increasing"
            )
            assert all(b > a for a, b in zip(seqs, seqs[1:])), (
                "seq not strictly increasing"
            )

            # Grab is rejected while streaming.
            grab = _grab(session, realm, cid, {"encoding": ENCODING_JPEG})
            assert grab.ok is False
            assert grab.error
        finally:
            ack = _query_ack(session, keys.cmd_stream_stop(realm, cid), {})
            assert ack.ok, ack.error

        time.sleep(0.5)
        late = collect_frames(session, keys.image(realm, cid), duration_s=1.0)
        assert not late, f"frames still flowing after stream_stop: {len(late)}"

        # stream_stop is idempotent.
        ack = _query_ack(session, keys.cmd_stream_stop(realm, cid), {})
        assert ack.ok, ack.error
    finally:
        ack = _query_ack(
            session, keys.cmd_configure(realm, cid), {"auto_exposure": True}
        )
        assert ack.ok, ack.error


def test_configure_roundtrip(session, realm, cid):
    status = CameraStatus.from_wire(
        first_sample(session, keys.state_status(realm, cid), timeout_s=3.0)
    )
    assert status.exposure_us is not None, "no exposure in status"
    target = float(status.exposure_us)

    ack = _query_ack(
        session,
        keys.cmd_configure(realm, cid),
        {"auto_exposure": False, "exposure_us": target},
    )
    assert ack.ok, ack.error
    try:
        deadline = time.monotonic() + 3.0
        seen: float | None = None
        while time.monotonic() < deadline:
            samples = collect_samples(
                session, keys.state_status(realm, cid), duration_s=1.5, min_count=1
            )
            for sample in samples:
                exposure = CameraStatus.from_wire(sample).exposure_us
                if exposure is not None:
                    seen = exposure
            if seen is not None and abs(seen - target) <= max(0.05 * target, 5.0):
                break
        assert seen is not None, "no exposure readback in status"
        assert abs(seen - target) <= max(0.05 * target, 5.0), (
            f"exposure {seen} did not settle at {target}"
        )
    finally:
        ack = _query_ack(
            session, keys.cmd_configure(realm, cid), {"auto_exposure": True}
        )
        assert ack.ok, ack.error
