"""The recorder service (design §5.6): record ``{realm}/**`` to MCAP.

Crash-only: no state to restore; on restart everything is re-declared.
Control plane is realm-less (``recording/...``) so the recorder's own
traffic is never captured by the ``{realm}/**`` subscriber.

Run: ``python -m wf.services.recording.recorder``.
"""

from __future__ import annotations

import argparse
import os
import queue
import threading
import time

import zenoh

from wf.core.codec import decode, encode
from wf.core.keys import realm_prefix
from wf.core.log import get_logger
from wf.core.session import open_session
from wf.core.time import now_ns

from . import keys
from .sink import McapSink

_log = get_logger("wf.services.recording.recorder")

_QUEUE_MAX = 8192
_WRITER_JOIN_TIMEOUT_S = 5.0

_SENTINEL = None
_KIND_DATA = "data"
_KIND_MARK = "mark"


class Recorder:
    def __init__(
        self,
        session: zenoh.Session,
        *,
        default_realm: str = "live",
        out_dir: str = "recordings",
    ) -> None:
        self.session = session
        self.default_realm = default_realm
        self.out_dir = out_dir

        self._lock = threading.Lock()  # guards the recording state transitions
        self._stop_event = threading.Event()
        self._queryables: list = []
        self._pub_state: zenoh.Publisher | None = None
        self._alive_token = None

        # Active-recording state (all None/zero when idle).
        self._sink: McapSink | None = None
        self._queue: queue.Queue | None = None
        self._writer_thread: threading.Thread | None = None
        self._subscriber = None
        self._realm: str | None = None
        self._dropped = 0
        self._deleted = 0

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._queryables = [
            self.session.declare_queryable(keys.cmd_start(), self._on_cmd_start),
            self.session.declare_queryable(keys.cmd_stop(), self._on_cmd_stop),
            self.session.declare_queryable(keys.cmd_mark(), self._on_cmd_mark),
        ]
        self._pub_state = self.session.declare_publisher(keys.state())
        # `declare_alive` cannot build realm-less keys; same underlying call.
        self._alive_token = self.session.liveliness().declare_token(
            keys.recorder_alive()
        )
        self._publish_state()
        _log.info("recorder up: default_realm=%s out_dir=%s", self.default_realm, self.out_dir)

    def run_forever(self) -> None:
        try:
            while not self._stop_event.wait(1.0):
                if self._sink is not None:
                    self._publish_state()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self._stop_event.set()
        with self._lock:
            if self._sink is not None:
                result = self._stop_recording_locked()
                _log.info("recording closed on shutdown: %s", result)
        _log.info("recorder stopped")

    # ── recording control ────────────────────────────────────────────────

    def start_recording(
        self, realm: str | None = None, label: str | None = None
    ) -> str:
        """Start recording ``{realm}/**``; returns the output file path."""
        with self._lock:
            if self._sink is not None:
                raise ValueError("already_recording")
            realm = realm_prefix(realm or self.default_realm)

            os.makedirs(self.out_dir, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            name = f"{realm.replace('/', '-')}_{stamp}"
            if label:
                name += f"_{label}"
            path = os.path.join(self.out_dir, f"{name}.mcap")

            sink = McapSink(path, realm)
            q: queue.Queue = queue.Queue(maxsize=_QUEUE_MAX)
            writer = threading.Thread(
                target=self._writer_loop, args=(q, sink), name="mcap-writer", daemon=True
            )
            writer.start()

            self._sink = sink
            self._queue = q
            self._writer_thread = writer
            self._realm = realm
            self._dropped = 0
            self._deleted = 0
            # Subscribe LAST: nothing reaches the queue before this point.
            self._subscriber = self.session.declare_subscriber(
                f"{realm}/**", self._on_sample
            )
        self._publish_state()
        _log.info("recording started: realm=%s path=%s", realm, path)
        return path

    def stop_recording(self) -> dict:
        with self._lock:
            if self._sink is None:
                raise ValueError("not_recording")
            result = self._stop_recording_locked()
        self._publish_state()
        _log.info("recording stopped: %s", result)
        return result

    def _stop_recording_locked(self) -> dict:
        # Undeclare the subscriber FIRST so no new samples land in the queue.
        self._subscriber.undeclare()
        self._queue.put(_SENTINEL)
        self._writer_thread.join(timeout=_WRITER_JOIN_TIMEOUT_S)
        sink = self._sink
        sink.close()
        self._sink = None
        self._queue = None
        self._writer_thread = None
        self._subscriber = None
        self._realm = None
        return {"path": sink.path, "messages": sink.message_count}

    def mark(self, label: str) -> str | None:
        """Insert a mark; returns an error token or None on success."""
        if not label:
            return "empty_label"
        with self._lock:
            if self._sink is None:
                return "not_recording"
            # Through the same queue so ordering vs. data messages holds.
            try:
                self._queue.put_nowait((_KIND_MARK, label, now_ns()))
            except queue.Full:
                return "queue_full"
        return None

    # ── data path ────────────────────────────────────────────────────────

    def _on_sample(self, sample: zenoh.Sample) -> None:
        # Zenoh callback thread: never block.
        if sample.kind != zenoh.SampleKind.PUT:
            self._deleted += 1
            _log.debug("skipping non-PUT sample on %s", sample.key_expr)
            return
        q = self._queue
        if q is None:
            return
        attachment = sample.attachment
        item = (
            _KIND_DATA,
            str(sample.key_expr),
            sample.payload.to_bytes(),
            attachment.to_bytes() if attachment is not None else None,
            now_ns(),
        )
        try:
            q.put_nowait(item)
        except queue.Full:
            self._dropped += 1
            if self._dropped % 1000 == 1:
                _log.warning("recorder queue full; dropped %d samples", self._dropped)

    def _writer_loop(self, q: queue.Queue, sink: McapSink) -> None:
        while True:
            item = q.get()
            if item is _SENTINEL:
                return
            if item[0] == _KIND_MARK:
                _, label, t_ns = item
                sink.write_mark(label, t_ns)
            else:
                _, topic, payload, attachment, recv_ns = item
                sink.write(topic, payload, attachment, recv_ns)

    # ── control queryables ───────────────────────────────────────────────

    def _on_cmd_start(self, query: zenoh.Query) -> None:
        key = str(query.key_expr)
        try:
            req = decode(query.payload) if query.payload is not None else {}
            path = self.start_recording(req.get("realm"), req.get("label"))
            query.reply(
                key,
                encode(
                    {"ok": True, "error": None, "path": path, "realm": self._realm}
                ),
            )
        except ValueError as exc:
            query.reply(
                key,
                encode(
                    {"ok": False, "error": str(exc), "path": None, "realm": None}
                ),
            )
        except Exception as exc:
            query.reply(
                key,
                encode(
                    {"ok": False, "error": repr(exc), "path": None, "realm": None}
                ),
            )

    def _on_cmd_stop(self, query: zenoh.Query) -> None:
        key = str(query.key_expr)
        try:
            result = self.stop_recording()
            query.reply(
                key,
                encode(
                    {
                        "ok": True,
                        "error": None,
                        "path": result["path"],
                        "messages": result["messages"],
                    }
                ),
            )
        except ValueError as exc:
            query.reply(
                key,
                encode(
                    {"ok": False, "error": str(exc), "path": None, "messages": 0}
                ),
            )
        except Exception as exc:
            query.reply(
                key,
                encode(
                    {"ok": False, "error": repr(exc), "path": None, "messages": 0}
                ),
            )

    def _on_cmd_mark(self, query: zenoh.Query) -> None:
        key = str(query.key_expr)
        try:
            req = decode(query.payload) if query.payload is not None else {}
            error = self.mark(req.get("label") or "")
            query.reply(key, encode({"ok": error is None, "error": error}))
        except Exception as exc:
            query.reply(key, encode({"ok": False, "error": repr(exc)}))

    # ── state ────────────────────────────────────────────────────────────

    def _publish_state(self) -> None:
        if self._pub_state is None:
            return
        sink = self._sink
        self._pub_state.put(
            encode(
                {
                    "t": now_ns(),
                    "recording": sink is not None,
                    "path": sink.path if sink is not None else None,
                    "realm": self._realm,
                    "messages": sink.message_count if sink is not None else 0,
                    "dropped": self._dropped,
                }
            )
        )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="recorder", description=__doc__)
    parser.add_argument(
        "--realm",
        default=os.environ.get("WF_REALM", "live"),
        help="realm to record (default env WF_REALM or 'live')",
    )
    parser.add_argument(
        "--out-dir", default="recordings", help="output directory (default recordings)"
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    parser.add_argument(
        "--autostart",
        action="store_true",
        help="start recording immediately instead of waiting for cmd/start",
    )
    args = parser.parse_args(argv)

    session = open_session(args.zenoh_config)
    recorder = Recorder(session, default_realm=args.realm, out_dir=args.out_dir)
    try:
        recorder.start()
        if args.autostart:
            recorder.start_recording()
        recorder.run_forever()
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
