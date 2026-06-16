"""The replayer service (design §5.7): replay an MCAP file into ``replay/{session}/**``.

Keys recorded under the source realm are rewritten to the replay realm;
payload bytes are republished VERBATIM (original timestamps stay inside the
payloads — design §2). A clock topic carries replay data-time.

Run: ``python -m wf.services.recording.replayer <file.mcap>``.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import threading
import time

import zenoh

from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.core.session import declare_alive, open_session
from wf.core.time import now_ns

from . import keys
from .source import LogSource, McapSource

_log = get_logger("wf.services.recording.replayer")

_SLEEP_SLICE_S = 0.05
_CLOCK_PERIOD_S = 0.1  # 10 Hz while playing
_MAX_RATE = 64.0


class Replayer:
    def __init__(
        self,
        session: zenoh.Session,
        source: LogSource,
        *,
        session_id: str,
        rate: float = 1.0,
        start_paused: bool = False,
        source_realm: str | None = None,
    ) -> None:
        if not 0 < rate <= _MAX_RATE:
            raise ValueError(f"invalid rate {rate!r}")
        self.session = session
        self.source = source
        self.session_id = session_id
        self.replay_realm = keys.replay_realm(session_id)

        if source_realm is None:
            for metadata in source.topics().values():
                source_realm = metadata.get("realm")
                if source_realm:
                    break
        if not source_realm:
            raise ValueError("source realm unknown; pass --source-realm")
        self.source_realm = source_realm

        start_ns, end_ns = source.time_range()
        self._start_ns = start_ns
        self._end_ns = end_ns

        self._lock = threading.Lock()  # anchors, rate, flags
        self._stop_event = threading.Event()
        self._playing = not start_paused
        self._rate = rate
        self._position = start_ns  # data-time ns
        self._eof = False
        self._seek_generation = 0  # bumped on seek -> playback restarts iteration
        self._anchor_wall = 0
        self._anchor_data = start_ns

        self._publishers: dict[str, zenoh.Publisher] = {}
        self._alive_tokens: list = []
        self._queryables: list = []
        self._pub_clock: zenoh.Publisher | None = None
        self._playback_thread: threading.Thread | None = None
        self._marks: list[dict] | None = None

    # ── key rewrite ──────────────────────────────────────────────────────

    def _rewrite(self, topic: str) -> str | None:
        """Source-realm topic -> replay-realm key; None = skip (e.g. marks)."""
        prefix = f"{self.source_realm}/"
        if not topic.startswith(prefix):
            return None
        return f"{self.replay_realm}/{topic[len(prefix):]}"

    def _publisher(self, rewritten: str) -> zenoh.Publisher:
        pub = self._publishers.get(rewritten)
        if pub is None:
            pub = self.session.declare_publisher(rewritten)
            self._publishers[rewritten] = pub
        return pub

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        # Liveliness for every (contract, rid) seen in the file, so realm
        # consumers' liveliness badges work in replay for free.
        seen: set[tuple[str, str]] = set()
        realm_depth = self.replay_realm.count("/") + 1
        for topic in self.source.topics():
            rewritten = self._rewrite(topic)
            if rewritten is None:
                continue
            parts = rewritten.split("/")
            if len(parts) < realm_depth + 2:
                continue
            contract, rid = parts[realm_depth], parts[realm_depth + 1]
            if (contract, rid) not in seen:
                seen.add((contract, rid))
                self._alive_tokens.append(
                    declare_alive(
                        self.session, f"replay/{self.session_id}", contract, rid
                    )
                )

        self._pub_clock = self.session.declare_publisher(
            keys.replay_clock(self.session_id)
        )
        self._queryables = [
            self.session.declare_queryable(
                keys.replay_cmd(self.session_id, "play"), self._on_play
            ),
            self.session.declare_queryable(
                keys.replay_cmd(self.session_id, "pause"), self._on_pause
            ),
            self.session.declare_queryable(
                keys.replay_cmd(self.session_id, "seek"), self._on_seek
            ),
            self.session.declare_queryable(
                keys.replay_cmd(self.session_id, "rate"), self._on_rate
            ),
            self.session.declare_queryable(
                keys.replay_cmd(self.session_id, "info"), self._on_info
            ),
        ]

        self._playback_thread = threading.Thread(
            target=self._playback_loop, name="replay-playback", daemon=True
        )
        self._playback_thread.start()
        self._publish_clock()
        _log.info(
            "replayer up: session=%s source_realm=%s range=(%d, %d)",
            self.session_id,
            self.source_realm,
            self._start_ns,
            self._end_ns,
        )

    def run_forever(self) -> None:
        try:
            while not self._stop_event.wait(1.0):
                pass
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self._stop_event.set()
        if self._playback_thread is not None:
            self._playback_thread.join(timeout=5.0)
        _log.info("replayer stopped")

    # ── playback ─────────────────────────────────────────────────────────

    def _publish_record(self, rewritten: str, payload: bytes, attachment) -> None:
        pub = self._publisher(rewritten)
        if attachment is not None:
            pub.put(payload, attachment=attachment)
        else:
            pub.put(payload)

    def _playback_loop(self) -> None:
        try:
            self._run_playback()
        except Exception:
            # A dead playback thread must not leave a lying playing=True
            # status behind (zombie replayer).
            _log.exception("playback loop crashed")
            with self._lock:
                self._playing = False
            self._publish_clock()

    def _run_playback(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                generation = self._seek_generation
                start = self._position
                self._anchor_wall = now_ns()
                self._anchor_data = start
            interrupted = self._play_from(start, generation)
            if interrupted:
                continue  # seek happened -> restart iteration from new position
            # EOF
            with self._lock:
                self._playing = False
                self._eof = True
                self._position = self._end_ns
            self._publish_clock()
            # Stay alive for seeks (scrubbing); wait for a state change.
            while not self._stop_event.is_set():
                with self._lock:
                    if self._seek_generation != generation:
                        break
                time.sleep(_SLEEP_SLICE_S)

    def _play_from(self, start_ns: int, generation: int) -> bool:
        """Play records from ``start_ns``. True = interrupted by seek."""
        next_clock = 0.0
        for record in self.source.iter_records(start_ns=start_ns):
            rewritten = self._rewrite(record.topic)
            # Pace to the record's log_time (marks too: they hold the slot).
            while True:
                if self._stop_event.is_set():
                    return True
                with self._lock:
                    if self._seek_generation != generation:
                        return True
                    playing = self._playing
                    if playing:
                        target_wall = self._anchor_wall + int(
                            (record.log_time - self._anchor_data) / self._rate
                        )
                        delay_s = (target_wall - now_ns()) / 1e9
                if not playing:
                    time.sleep(_SLEEP_SLICE_S)
                    continue
                if delay_s <= 0:
                    break
                time.sleep(min(delay_s, _SLEEP_SLICE_S))
            if rewritten is not None:
                self._publish_record(rewritten, record.payload, record.attachment)
            with self._lock:
                self._position = record.log_time
            now_mono = time.monotonic()
            if now_mono >= next_clock:
                next_clock = now_mono + _CLOCK_PERIOD_S
                self._publish_clock()
        return False

    # ── controls ─────────────────────────────────────────────────────────

    def _status(self) -> dict:
        with self._lock:
            return {
                "ok": True,
                "error": None,
                "t_data": self._position,
                "rate": self._rate,
                "playing": self._playing,
            }

    def _reply(self, query: zenoh.Query, status: dict) -> None:
        query.reply(str(query.key_expr), encode(status))

    def _on_play(self, query: zenoh.Query) -> None:
        try:
            with self._lock:
                if not self._playing and not self._eof:
                    self._playing = True
                    self._anchor_wall = now_ns()
                    self._anchor_data = self._position
            self._publish_clock()
            self._reply(query, self._status())
        except Exception as exc:
            self._reply(query, self._error_status(repr(exc)))

    def _on_pause(self, query: zenoh.Query) -> None:
        try:
            with self._lock:
                self._playing = False
            self._publish_clock()
            self._reply(query, self._status())
        except Exception as exc:
            self._reply(query, self._error_status(repr(exc)))

    def _on_seek(self, query: zenoh.Query) -> None:
        try:
            req = decode(query.payload) if query.payload is not None else {}
            t_ns = req.get("t_ns")
            if not isinstance(t_ns, int) or isinstance(t_ns, bool):
                self._reply(query, self._error_status("missing t_ns"))
                return
            self.seek(t_ns)
            self._reply(query, self._status())
        except Exception as exc:
            self._reply(query, self._error_status(repr(exc)))

    def _on_rate(self, query: zenoh.Query) -> None:
        try:
            req = decode(query.payload) if query.payload is not None else {}
            rate = req.get("rate")
            if (
                not isinstance(rate, (int, float))
                or isinstance(rate, bool)
                or not 0 < rate <= _MAX_RATE
            ):
                self._reply(query, self._error_status("invalid rate"))
                return
            with self._lock:
                self._rate = float(rate)
                self._anchor_wall = now_ns()
                self._anchor_data = self._position
            self._publish_clock()
            self._reply(query, self._status())
        except Exception as exc:
            self._reply(query, self._error_status(repr(exc)))

    def _get_marks(self) -> list[dict]:
        """Marks ({"t": int, "label": str}) in file order; O(file) once, cached."""
        if self._marks is None:
            self._marks = [
                decode(record.payload)
                for record in self.source.iter_records()
                if record.topic == keys.MARKS_TOPIC
            ]
        return self._marks

    def _on_info(self, query: zenoh.Query) -> None:
        try:
            self._reply(
                query,
                {
                    **self._status(),
                    "start_ns": self._start_ns,
                    "end_ns": self._end_ns,
                    "source_realm": self.source_realm,
                    "marks": self._get_marks(),
                },
            )
        except Exception as exc:
            self._reply(query, self._error_status(repr(exc)))

    def _error_status(self, error: str) -> dict:
        with self._lock:
            return {
                "ok": False,
                "error": error,
                "t_data": self._position,
                "rate": self._rate,
                "playing": self._playing,
            }

    def seek(self, t_ns: int) -> None:
        """Jump to data-time ``t_ns`` (clamped); republish latest-per-topic."""
        t_ns = max(self._start_ns, min(t_ns, self._end_ns))
        # Latest record per topic with log_time <= t: O(file) scan, accepted
        # this phase (recordings are minutes long).
        latest: dict[str, tuple[bytes, bytes | None]] = {}
        for record in self.source.iter_records():
            if record.log_time > t_ns:
                break
            rewritten = self._rewrite(record.topic)
            if rewritten is not None:
                latest[rewritten] = (record.payload, record.attachment)
        with self._lock:
            self._position = t_ns
            self._anchor_wall = now_ns()
            self._anchor_data = t_ns
            self._eof = False
            self._seek_generation += 1
        for rewritten, (payload, attachment) in latest.items():
            self._publish_record(rewritten, payload, attachment)
        self._publish_clock()

    # ── clock ────────────────────────────────────────────────────────────

    def _publish_clock(self) -> None:
        if self._pub_clock is None:
            return
        with self._lock:
            msg = {
                "t": now_ns(),
                "t_data": self._position,
                "rate": self._rate,
                "playing": self._playing,
            }
        self._pub_clock.put(encode(msg))


def _default_session_id(path: str) -> str:
    stem = os.path.splitext(os.path.basename(path))[0].lower()
    return re.sub(r"[^a-z0-9_-]", "-", stem)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="replayer", description=__doc__)
    parser.add_argument("file", help="MCAP recording path")
    parser.add_argument(
        "--session", default=None, help="replay session id (default: file stem)"
    )
    parser.add_argument("--rate", type=float, default=1.0)
    parser.add_argument("--start-paused", action="store_true")
    parser.add_argument(
        "--source-realm",
        default=None,
        help="realm recorded in the file (default: channel metadata)",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    session_id = args.session or _default_session_id(args.file)
    source = McapSource(args.file)

    source_realm = args.source_realm
    if source_realm is None:
        for metadata in source.topics().values():
            source_realm = metadata.get("realm")
            if source_realm:
                break
    if not source_realm or not any(
        topic.startswith(f"{source_realm}/") for topic in source.topics()
    ):
        print(
            f"no topics under source realm {source_realm!r} in {args.file}",
            file=sys.stderr,
        )
        source.close()
        return 1

    session = open_session(args.zenoh_config)
    replayer = Replayer(
        session,
        source,
        session_id=session_id,
        rate=args.rate,
        start_paused=args.start_paused,
        source_realm=source_realm,
    )
    try:
        replayer.start()
        replayer.run_forever()
    finally:
        source.close()
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
