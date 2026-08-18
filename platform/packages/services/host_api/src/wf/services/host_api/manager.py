"""``SupervisorManager``: exactly one cell runs on this host (one bus, realm
``cell``). Activating a cell stops the running supervisor *tree* (supervisor +
its providers + program runner) and starts the chosen cell's supervisor. The
config store service is realm-less and owned here so it survives switches.
The last choice is persisted (``<deploy>/host.yaml``) and restored on start.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import yaml

from wf.core.log import get_logger

from .cells import CellInfo, scan_cells

_log = get_logger("wf.services.host_api")

_STATE_FILE = "host.yaml"


def _tree_kill(proc: subprocess.Popen, timeout: float = 10.0) -> None:
    """Terminate a child and everything it spawned."""
    if proc.poll() is not None:
        return
    if os.name == "nt":
        # The child was started in its own process group: Ctrl-Break reaches
        # it as KeyboardInterrupt (the supervisor then reaps its children);
        # taskkill the tree for whatever is left.
        try:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
            proc.wait(timeout=timeout)
        except Exception:
            pass
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, check=False)
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=timeout)
        except Exception:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
    try:
        proc.wait(timeout=5.0)
    except Exception:
        pass


def _popen_group(argv: list[str], log_path: Path | None) -> subprocess.Popen:
    kwargs: dict = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    stdout = open(log_path, "ab") if log_path is not None else None  # noqa: SIM115
    return subprocess.Popen(argv, stdout=stdout, stderr=subprocess.STDOUT if stdout else None, **kwargs)


class SupervisorManager:
    def __init__(self, deploy_root: str, *, realm: str = "cell", zenoh_config: str | None = None,
                 with_config: bool = False, config_dir: str | None = None, log_dir: str | None = None,
                 supervisor_argv: list[str] | None = None):
        self.deploy_root = Path(deploy_root)
        self.realm = realm
        self.zenoh_config = zenoh_config
        self.with_config = with_config
        self.config_dir = config_dir or str(self.deploy_root / "config")
        self.log_dir = Path(log_dir) if log_dir else self.deploy_root / "logs"
        # Test seam: what to run instead of ``python -m wf.services.supervisor``.
        self._supervisor_argv = supervisor_argv
        self._lock = threading.RLock()
        self._proc: subprocess.Popen | None = None
        self._config_proc: subprocess.Popen | None = None
        self._active: dict | None = None  # {cell, runtime, since}

    # ── registry ─────────────────────────────────────────────────────────

    def cells(self) -> list[CellInfo]:
        return scan_cells(self.deploy_root)

    def cell(self, cid: str) -> CellInfo | None:
        return next((c for c in self.cells() if c.id == cid), None)

    # ── state ────────────────────────────────────────────────────────────

    def status(self) -> dict:
        with self._lock:
            alive = self._proc is not None and self._proc.poll() is None
            return {
                "active": dict(self._active) if self._active else None,
                "alive": alive,
                "pid": self._proc.pid if self._proc is not None else None,
                "config_alive": self._config_proc is not None and self._config_proc.poll() is None,
            }

    def _state_path(self) -> Path:
        return self.deploy_root / _STATE_FILE

    def _persist(self) -> None:
        try:
            data = {"active": {k: v for k, v in (self._active or {}).items() if k in ("cell", "runtime")}}
            self._state_path().write_text(yaml.safe_dump(data), encoding="utf-8")
        except Exception:
            _log.debug("persist failed", exc_info=True)

    def restore(self) -> dict | None:
        """The persisted last choice ({cell, runtime}) or None."""
        p = self._state_path()
        if not p.exists():
            return None
        try:
            data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            active = data.get("active") or {}
            if isinstance(active, dict) and active.get("cell"):
                return {"cell": str(active["cell"]), "runtime": active.get("runtime")}
        except Exception:
            _log.warning("could not read %s", p, exc_info=True)
        return None

    # ── lifecycle ────────────────────────────────────────────────────────

    def start_config(self) -> None:
        if not self.with_config:
            return
        with self._lock:
            if self._config_proc is not None and self._config_proc.poll() is None:
                return
            argv = [sys.executable, "-m", "wf.services.config", "--dir", self.config_dir]
            if self.zenoh_config:
                argv += ["--zenoh-config", self.zenoh_config]
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._config_proc = _popen_group(argv, self.log_dir / "config.log")
            _log.info("config service pid=%s", self._config_proc.pid)

    def activate(self, cid: str, runtime: str | None) -> dict:
        """Switch to cell ``cid`` with overlay ``runtime`` (id; None = the
        overlay named ``default`` if present, else the first, else none)."""
        info = self.cell(cid)
        if info is None:
            raise KeyError(f"unknown_cell:{cid}")
        if info.error is not None:
            raise ValueError(f"bad_cell:{cid}:{info.error}")
        if runtime is None:
            runtime = "default" if "default" in info.runtimes else (sorted(info.runtimes)[0] if info.runtimes else None)
        if runtime is not None and runtime not in info.runtimes:
            raise KeyError(f"unknown_runtime:{cid}:{runtime}")
        with self._lock:
            self.stop()
            argv = self._argv(info, runtime)
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self._proc = _popen_group(argv, self.log_dir / "supervisor.log")
            self._active = {"cell": cid, "runtime": runtime, "since": time.time()}
            self._persist()
            _log.info("activated cell=%s runtime=%s pid=%s", cid, runtime, self._proc.pid)
            return self.status()

    def _argv(self, info: CellInfo, runtime: str | None) -> list[str]:
        if self._supervisor_argv is not None:
            return list(self._supervisor_argv)
        argv = [sys.executable, "-m", "wf.services.supervisor", "--cell", info.path, "--realm", self.realm]
        if runtime is not None:
            argv += ["--runtime", info.runtimes[runtime]]
        if info.programs:
            argv += ["--programs", info.programs]
        if self.zenoh_config:
            argv += ["--zenoh-config", self.zenoh_config]
        return argv

    def stop(self) -> dict:
        with self._lock:
            if self._proc is not None:
                _log.info("stopping supervisor pid=%s", self._proc.pid)
                _tree_kill(self._proc)
                self._proc = None
            self._active = None
            self._persist()
            return self.status()

    def close(self) -> None:
        with self._lock:
            self.stop()
            if self._config_proc is not None:
                _tree_kill(self._config_proc)
                self._config_proc = None
