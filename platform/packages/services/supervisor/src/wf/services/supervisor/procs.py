"""Module map + subprocess spawner for the supervisor.

The supervisor spawns ``python -m wf.<pkg> ...`` children via ``Popen`` (no
Docker socket); ``sys.executable`` is the frozen pixi-env python so children
inherit the env and import ``wf.*``. ``ProcManager`` owns the children and
reaps them on stop / shutdown.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import time

from wf.core.log import get_logger

_log = get_logger("wf.services.supervisor.procs")

# How a source provider is brought up (from the cell source's ``launch:``).
LAUNCH_MODULE = "module"  # spawn ``python -m <module>`` as a supervisor child
LAUNCH_EXTERNAL = "external"  # served by a process OUTSIDE the supervisor

# (contract, provider kind) -> module for supervisor-launched providers.
# External providers such as the headless browser camera remain in the device
# inventory but are managed outside the supervisor.
PROVIDER_MODULES: dict[tuple[str, str], str] = {
    ("arm", "arm_sim"): "wf.hal.arm_sim",
    ("arm", "aubo_i10"): "wf.hal.aubo_i10",
    ("arm", "replay_arm"): "wf.hal.replay.arm",
    ("camera2d", "genicam"): "wf.hal.genicam",
    ("camera2d", "replay_camera"): "wf.hal.replay.camera",
    ("camera2d", "browser_camera"): "wf.hal.browser_camera",
    ("dio", "sim_dio"): "wf.hal.sim_dio",
}


def provider_module(contract: str, kind: str) -> str:
    """Module to spawn for a module-launched provider; raises on unknown kind."""
    module = PROVIDER_MODULES.get((contract, kind))
    if module is None:
        raise ValueError(f"bad_cell:unknown_provider:{contract}:{kind}")
    return module


# A freshly-spawned child that exits within this window is treated as a failed
# spawn (e.g. import error, bad args) rather than a transient running process.
_SPAWN_SETTLE_S = 0.5


class ProcManager:
    """Owns ``subprocess.Popen`` children keyed by a logical name."""

    def __init__(self) -> None:
        self._procs: dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()

    def spawn(self, name: str, argv: list[str], *, env=None) -> None:
        """Spawn ``[sys.executable, "-m", *argv]`` under ``name``.

        Raises ``RuntimeError("spawn_failed:<name>")`` if ``Popen`` raises or
        the child exits within the settle window.
        """
        with self._lock:
            if name in self._procs and self._procs[name].poll() is None:
                raise RuntimeError(f"spawn_failed:{name}")  # already running
            try:
                proc = subprocess.Popen([sys.executable, "-m", *argv], env=env)
            except Exception as exc:  # noqa: BLE001
                _log.error("spawn %s failed: %r", name, exc)
                raise RuntimeError(f"spawn_failed:{name}") from exc
            self._procs[name] = proc
        time.sleep(_SPAWN_SETTLE_S)
        if proc.poll() is not None:
            _log.error("spawn %s exited immediately rc=%s", name, proc.returncode)
            with self._lock:
                self._procs.pop(name, None)
            raise RuntimeError(f"spawn_failed:{name}")
        _log.info("spawned %s pid=%s", name, proc.pid)

    def alive(self, name: str) -> bool:
        with self._lock:
            proc = self._procs.get(name)
        return proc is not None and proc.poll() is None

    def stop(self, name: str, *, timeout: float = 10.0) -> bool:
        """Terminate the named child; returns True if it was tracked."""
        with self._lock:
            proc = self._procs.pop(name, None)
        if proc is None:
            return False
        self._reap(name, proc, timeout)
        return True

    def stop_all(self, *, timeout: float = 10.0) -> None:
        with self._lock:
            items = list(self._procs.items())
            self._procs.clear()
        for name, proc in items:
            self._reap(name, proc, timeout)

    def reap_dead(self) -> list[str]:
        """Drop children that have exited on their own; return their names."""
        dead: list[str] = []
        with self._lock:
            for name, proc in list(self._procs.items()):
                if proc.poll() is not None:
                    dead.append(name)
                    del self._procs[name]
        for name in dead:
            _log.warning("child %s exited unexpectedly", name)
        return dead

    def names(self) -> list[str]:
        with self._lock:
            return [n for n, p in self._procs.items() if p.poll() is None]

    @staticmethod
    def _reap(name: str, proc: subprocess.Popen, timeout: float) -> None:
        if proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _log.warning("child %s did not terminate; killing", name)
            proc.kill()
            proc.wait()
        _log.info("reaped %s", name)
