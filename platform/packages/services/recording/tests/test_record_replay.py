"""Record/replay fidelity suite over a real zenoh peer link (no router, no hardware).

Phase gate for roadmap §10.2: byte-for-byte record proof, realm-rewrite
replay proof, §5.7 control surface, crash-file guard.
"""

from __future__ import annotations

import threading
import time

import cbor2
import pytest

from wf.core.codec import decode, encode
from wf.core.testing import linked_sessions
from wf.core.time import now_ns
from wf.services.recording import keys
from wf.services.recording.recorder import Recorder
from wf.services.recording.replayer import Replayer
from wf.services.recording.sink import McapSink
from wf.services.recording.source import McapSource

JOINTS_KEY = "live/arm/r9/state/joints"
IO_KEY = "live/arm/r9/state/io"


@pytest.fixture
def linked():
    with linked_sessions() as (session_a, session_b):
        yield session_a, session_b


def _query(session, key: str, payload: dict, timeout_s: float = 5.0) -> dict | None:
    replies = session.get(key, payload=encode(payload), timeout=timeout_s)
    for reply in replies:
        if reply.ok is not None:
            return decode(reply.ok.payload)
    return None


def _wait_until(predicate, timeout_s: float, message: str) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(message)


# ── test 1: record round-trip fidelity ──────────────────────────────────


def test_record_roundtrip_fidelity(linked, tmp_path):
    session_a, session_b = linked
    recorder = Recorder(session_b, out_dir=str(tmp_path))
    recorder.start()
    time.sleep(0.5)  # queryable/route propagation

    reply = _query(session_a, keys.cmd_start(), {"label": "t1"})
    assert reply is not None and reply["ok"], reply
    path = reply["path"]
    assert path and path.endswith("_t1.mcap")
    assert reply["realm"] == "live"
    time.sleep(0.5)  # subscriber propagation

    t0 = now_ns()
    sent_joints: list[bytes] = []
    sent_io: list[tuple[bytes, bytes | None]] = []

    for i in range(200):
        payload = encode(
            {
                "t": t0 + i * 5_000_000,
                "q": [float(i)] * 6,
                "qd": [0.0] * 6,
                "tau": [0.0] * 6,
                "clock_domain": "host",
            }
        )
        sent_joints.append(payload)
        session_a.put(JOINTS_KEY, payload)
        if i == 100:
            mark_reply = _query(session_a, keys.cmd_mark(), {"label": "m1"})
            assert mark_reply is not None and mark_reply["ok"], mark_reply

    for i in range(20):
        payload = encode({"t": t0 + i * 50_000_000, "di": [i % 2] * 4})
        attachment = b"att-%d" % i if i < 5 else None
        sent_io.append((payload, attachment))
        if attachment is not None:
            session_a.put(IO_KEY, payload, attachment=attachment)
        else:
            session_a.put(IO_KEY, payload)

    time.sleep(1.0)  # drain
    reply = _query(session_a, keys.cmd_stop(), {})
    assert reply is not None and reply["ok"], reply
    assert reply["messages"] == 221
    recorder.shutdown()

    source = McapSource(path)
    try:
        topics = source.topics()
        assert set(topics) == {JOINTS_KEY, IO_KEY, keys.MARKS_TOPIC}
        for metadata in topics.values():
            assert metadata == {"realm": "live"}

        got_joints: list[bytes] = []
        got_io: list[tuple[bytes, bytes | None]] = []
        got_marks: list[dict] = []
        for record in source.iter_records():
            if record.topic == JOINTS_KEY:
                assert record.attachment is None
                got_joints.append(record.payload)
            elif record.topic == IO_KEY:
                got_io.append((record.payload, record.attachment))
            else:
                got_marks.append(cbor2.loads(record.payload))

        assert got_joints == sent_joints
        assert got_io == sent_io
        assert len(got_marks) == 1
        assert got_marks[0]["label"] == "m1"
        assert isinstance(got_marks[0]["t"], int)
    finally:
        source.close()


# ── fixture builder for replay tests ────────────────────────────────────


def _build_fixture(path: str) -> dict[str, list[tuple[bytes, bytes | None]]]:
    """2 topics + 1 mark; log_time spaced 5 ms; 3 attachments. Returns sent data."""
    t0 = 1_000_000_000_000  # deterministic data epoch
    sink = McapSink(path, "live")
    sent: dict[str, list[tuple[bytes, bytes | None]]] = {JOINTS_KEY: [], IO_KEY: []}
    for i in range(100):
        payload = encode({"t": t0 + i * 5_000_000, "q": [float(i)] * 6})
        sent[JOINTS_KEY].append((payload, None))
        sink.write(JOINTS_KEY, payload, None, t0 + i * 5_000_000)
    for i in range(10):
        payload = encode({"t": t0 + i * 50_000_000, "di": [i] * 4})
        attachment = b"fix-att-%d" % i if i < 3 else None
        sent[IO_KEY].append((payload, attachment))
        sink.write(IO_KEY, payload, attachment, t0 + 2_500_000 + i * 50_000_000)
    sink.write_mark("fixture-mark", t0 + 250_000_000)
    sink.close()
    return sent


class _Collector:
    def __init__(self):
        self.lock = threading.Lock()
        self.samples: list[tuple[str, bytes, bytes | None]] = []
        self.wall_times: list[float] = []

    def __call__(self, sample):
        attachment = sample.attachment
        with self.lock:
            self.samples.append(
                (
                    str(sample.key_expr),
                    sample.payload.to_bytes(),
                    attachment.to_bytes() if attachment is not None else None,
                )
            )
            self.wall_times.append(time.monotonic())

    def snapshot(self):
        with self.lock:
            return list(self.samples)

    def clear(self):
        with self.lock:
            self.samples.clear()
            self.wall_times.clear()


class _ClockCollector:
    def __init__(self):
        self.lock = threading.Lock()
        self.clocks: list[dict] = []

    def __call__(self, sample):
        with self.lock:
            self.clocks.append(decode(sample.payload))

    def latest(self) -> dict | None:
        with self.lock:
            return self.clocks[-1] if self.clocks else None

    def any_stopped(self) -> bool:
        with self.lock:
            return any(not c["playing"] for c in self.clocks)


# ── test 2: replay rewrite + fidelity ───────────────────────────────────


def test_replay_rewrites_and_preserves_bytes(linked, tmp_path):
    session_a, session_b = linked
    path = str(tmp_path / "fixture.mcap")
    sent = _build_fixture(path)

    data = _Collector()
    clock = _ClockCollector()
    sub_data = session_b.declare_subscriber("replay/pytest/arm/**", data)
    sub_clock = session_b.declare_subscriber(keys.replay_clock("pytest"), clock)
    time.sleep(0.5)  # subscriber propagation

    source = McapSource(path)
    replayer = Replayer(session_a, source, session_id="pytest", rate=8.0)
    try:
        replayer.start()
        _wait_until(clock.any_stopped, 15.0, "no EOF clock within 15 s")
        # All data published before the EOF clock; small settle for delivery.
        _wait_until(
            lambda: len(data.snapshot()) >= 110, 5.0, "replay samples missing"
        )
    finally:
        replayer.shutdown()
        sub_data.undeclare()
        sub_clock.undeclare()
        source.close()

    samples = data.snapshot()
    by_key: dict[str, list[tuple[bytes, bytes | None]]] = {}
    for key, payload, attachment in samples:
        by_key.setdefault(key, []).append((payload, attachment))

    expected_joints = f"replay/pytest/{JOINTS_KEY.removeprefix('live/')}"
    expected_io = f"replay/pytest/{IO_KEY.removeprefix('live/')}"
    assert expected_joints == "replay/pytest/arm/r9/state/joints"
    assert set(by_key) == {expected_joints, expected_io}
    assert by_key[expected_joints] == sent[JOINTS_KEY]
    assert by_key[expected_io] == sent[IO_KEY]
    # Nothing derived from recording/marks under the replay realm.
    assert not any("marks" in key for key, _, _ in samples)

    wall = data.wall_times
    assert wall[-1] - wall[0] < 5.0  # 0.55 s of data @ 8x; loose Windows bound


# ── test 3: replay controls ─────────────────────────────────────────────


def test_replay_controls(linked, tmp_path):
    session_a, session_b = linked
    path = str(tmp_path / "fixture.mcap")
    sent = _build_fixture(path)

    data = _Collector()
    clock = _ClockCollector()
    sub_data = session_b.declare_subscriber("replay/pytest/arm/**", data)
    sub_clock = session_b.declare_subscriber(keys.replay_clock("pytest"), clock)
    time.sleep(0.5)

    source = McapSource(path)
    replayer = Replayer(
        session_a, source, session_id="pytest", rate=1.0, start_paused=True
    )
    try:
        replayer.start()
        time.sleep(0.5)  # queryable propagation
        _wait_until(
            lambda: clock.latest() is not None, 5.0, "no initial clock sample"
        )
        assert clock.latest()["playing"] is False

        reply = _query(session_b, keys.replay_cmd("pytest", "play"), {})
        assert reply is not None and reply["ok"] and reply["playing"] is True
        _wait_until(
            lambda: (clock.latest() or {}).get("playing") is True,
            5.0,
            "clock never showed playing",
        )

        reply = _query(session_b, keys.replay_cmd("pytest", "pause"), {})
        assert reply is not None and reply["ok"] and reply["playing"] is False

        time.sleep(0.3)  # let in-flight publishes land
        data.clear()

        start_ns, end_ns = source.time_range()
        t_mid = (start_ns + end_ns) // 2
        reply = _query(session_b, keys.replay_cmd("pytest", "seek"), {"t_ns": t_mid})
        assert reply is not None and reply["ok"], reply
        assert reply["t_data"] == t_mid
        assert reply["playing"] is False

        expected_joints = f"replay/pytest/{JOINTS_KEY.removeprefix('live/')}"
        expected_io = f"replay/pytest/{IO_KEY.removeprefix('live/')}"
        _wait_until(
            lambda: len(data.snapshot()) >= 2, 5.0, "seek republish missing"
        )
        time.sleep(0.3)  # ensure nothing extra trickles in
        samples = data.snapshot()
        assert len(samples) == 2, samples
        got = {key: (payload, attachment) for key, payload, attachment in samples}
        # Last fixture record per topic with log_time <= t_mid.
        last_joints = sent[JOINTS_KEY][
            max(i for i in range(100) if 1_000_000_000_000 + i * 5_000_000 <= t_mid)
        ]
        last_io = sent[IO_KEY][
            max(
                i
                for i in range(10)
                if 1_000_000_000_000 + 2_500_000 + i * 50_000_000 <= t_mid
            )
        ]
        assert got[expected_joints] == last_joints
        assert got[expected_io] == last_io

        reply = _query(session_b, keys.replay_cmd("pytest", "rate"), {"rate": 4.0})
        assert reply is not None and reply["ok"] and reply["rate"] == 4.0

        reply = _query(session_b, keys.replay_cmd("pytest", "rate"), {"rate": 0})
        assert reply is not None and not reply["ok"]
        assert reply["error"] == "invalid rate"

        reply = _query(session_b, keys.replay_cmd("pytest", "info"), {})
        assert reply is not None and reply["ok"], reply
        assert (reply["start_ns"], reply["end_ns"]) == source.time_range()
        assert reply["source_realm"] == "live"
        assert reply["marks"] == [
            {"t": 1_000_000_000_000 + 250_000_000, "label": "fixture-mark"}
        ]
    finally:
        replayer.shutdown()
        sub_data.undeclare()
        sub_clock.undeclare()
        source.close()


# ── test 4: seek storm while playing ────────────────────────────────────


def test_seek_while_playing_keeps_playback_alive(linked, tmp_path):
    """Regression: a shared MCAP reader handle let the playback thread and a
    concurrent seek scan corrupt each other's file position, killing the
    playback thread silently (zombie playing=True, t_data frozen)."""
    session_a, session_b = linked
    path = str(tmp_path / "fixture.mcap")
    _build_fixture(path)

    clock = _ClockCollector()
    sub_clock = session_b.declare_subscriber(keys.replay_clock("pytest2"), clock)
    time.sleep(0.5)

    source = McapSource(path)
    replayer = Replayer(
        session_a, source, session_id="pytest2", rate=1.0, start_paused=True
    )
    try:
        replayer.start()
        time.sleep(0.5)  # queryable propagation
        start_ns, _end_ns = source.time_range()
        reply = _query(session_b, keys.replay_cmd("pytest2", "play"), {})
        assert reply is not None and reply["ok"], reply
        # Hammer seeks while the playback thread iterates concurrently.
        for i in range(10):
            t = start_ns + (i % 4) * 100_000_000
            reply = _query(session_b, keys.replay_cmd("pytest2", "seek"), {"t_ns": t})
            assert reply is not None and reply["ok"], reply
        last_target = start_ns + 100_000_000  # final seek (i=9 -> 9%4=1)
        # Playback must still advance past the final seek target (EOF also
        # satisfies this — end_ns > last_target); a dead thread stays frozen.
        _wait_until(
            lambda: (clock.latest() or {}).get("t_data", 0) > last_target,
            10.0,
            "playback did not advance after concurrent seeks",
        )
    finally:
        replayer.shutdown()
        sub_clock.undeclare()
        source.close()


# ── test 5: crash-file guard ────────────────────────────────────────────


def test_source_rejects_unfinalized_file(tmp_path):
    path = str(tmp_path / "crash.mcap")
    sink = McapSink(path, "live")
    sink.write(JOINTS_KEY, b"a", None, 1)
    sink.write(JOINTS_KEY, b"b", None, 2)
    sink.write(JOINTS_KEY, b"c", None, 3)
    sink._file.flush()  # crash: no close(), no MCAP summary/footer
    with pytest.raises(ValueError, match="not stopped cleanly"):
        McapSource(path)
