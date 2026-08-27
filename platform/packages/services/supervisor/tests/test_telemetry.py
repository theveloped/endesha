"""Child log capture (ProcManager pipes) and level parsing."""

from __future__ import annotations

import subprocess
import sys
import time

from wf.services.supervisor.procs import ProcManager
from wf.services.supervisor.telemetry import parse_level


def test_procmanager_captures_child_output():
    """The reader threads deliver both streams' lines to on_line.

    ``ProcManager.spawn`` runs ``python -m <module>``; to keep the test free of
    a throwaway module we spawn a ``-c`` child with the exact pipe wiring
    ``spawn`` uses and attach the manager's readers to it.
    """
    lines: list[tuple[str, str, str]] = []
    procs = ProcManager(on_line=lambda n, s, text: lines.append((n, s, text.rstrip())))
    proc = subprocess.Popen(
        [
            sys.executable,
            "-u",
            "-c",
            "import sys; print('hello INFO out'); print('boom ERROR err', file=sys.stderr)",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    procs._procs["child"] = proc
    procs._start_readers("child", proc)
    deadline = time.time() + 5.0
    while time.time() < deadline and len(lines) < 2:
        time.sleep(0.05)
    proc.wait(timeout=5.0)
    assert {stream for _, stream, _ in lines} == {"stdout", "stderr"}
    assert {text for _, _, text in lines} == {"hello INFO out", "boom ERROR err"}


def test_parse_level():
    assert parse_level("2026-08-27 10:00:00 INFO wf.hal.dio up", "stderr") == "info"
    assert parse_level("2026-08-27 10:00:00 WARNING wf.x slow", "stderr") == "warning"
    assert parse_level("2026-08-27 10:00:00 ERROR wf.x died", "stderr") == "error"
    assert parse_level("2026-08-27 10:00:00 CRITICAL wf.x gone", "stderr") == "error"
    assert parse_level("Traceback (most recent call last):", "stderr") == "error"
    assert parse_level("just some print", "stdout") == "info"
