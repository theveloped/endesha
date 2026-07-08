"""Shared wall-clock playback for per-device replay backends (RFC step 6).

``LoopPlayer`` opens an MCAP recording, iterates the records whose topic matches
a device predicate, paces them to their recorded ``log_time`` deltas (rate 1.0),
and loops continuously until stopped. Each matching record is handed to a
callback that re-stamps + republishes it via the device's core. A missing or
unreadable recording is surfaced as ``error`` (no crash), mirroring how the
genicam backend tolerates an absent camera.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import yaml

from wf.core.log import get_logger
from wf.core.time import now_ns
from wf.services.recording.source import McapSource

_log = get_logger("wf.hal.replay.playback")

_SLEEP_SLICE_S = 0.05


def read_resource_params(cell_yaml: str, rid: str) -> dict:
    """``resources[rid].params`` from a (realized) cell file — the supervisor
    writes a realized cell whose params merge shared config + the source's
    params (incl. ``recording``)."""
    cell = yaml.safe_load(Path(cell_yaml).read_text(encoding="utf-8")) or {}
    res = (cell.get("resources") or {}).get(rid) or {}
    return dict(res.get("params") or {})


class LoopPlayer:
    """Paces a recording's matching records to wall-clock and loops forever."""

    def __init__(self, recording, match, on_record):
        self.recording = recording  # path | None
        self.match = match  # predicate(topic) -> bool
        self.on_record = on_record  # callback(LogRecord)
        self.error: str | None = None
        self.source_realm: str | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if not self.recording:
            self.error = "no recording configured"
            _log.error("replay: no recording configured")
            return
        self._thread = threading.Thread(
            target=self._run, name="replay-playback", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3.0)

    def _run(self) -> None:
        try:
            source = McapSource(self.recording)
        except Exception as exc:  # noqa: BLE001
            self.error = f"recording unavailable: {exc!r}"
            _log.error("replay open failed: %r", exc)
            return
        self.source_realm = next(
            (m.get("realm") for m in source.topics().values() if m.get("realm")), None
        )
        try:
            while not self._stop.is_set():
                if not self._play_once(source):
                    # No matching records: avoid a hot loop; report + back off.
                    self.error = "no matching records for this device in the recording"
                    self._stop.wait(1.0)
        finally:
            source.close()

    def _play_once(self, source: McapSource) -> bool:
        """One pass through the recording, paced to log_time. Returns whether
        any matching record was produced."""
        anchor_wall: int | None = None
        anchor_data: int | None = None
        produced = False
        for record in source.iter_records():
            if self._stop.is_set():
                return produced
            if not self.match(record.topic):
                continue
            if anchor_wall is None:
                anchor_wall = now_ns()
                anchor_data = record.log_time
            target = anchor_wall + (record.log_time - anchor_data)
            delay = (target - now_ns()) / 1e9
            while delay > 0 and not self._stop.is_set():
                time.sleep(min(delay, _SLEEP_SLICE_S))
                delay = (target - now_ns()) / 1e9
            if self._stop.is_set():
                return produced
            try:
                self.on_record(record)
            except Exception:  # noqa: BLE001
                _log.warning("replay on_record failed", exc_info=True)
            else:
                self.error = None
            produced = True
        return produced
