"""Cell registry scan, the shipped deploy tree, and the API over a manager
whose 'supervisor' is a sleeping python child (activate/stop/tree-kill,
persistence, error codes)."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from wf.services.host_api import SupervisorManager, create_app, scan_cells

DEPLOY = Path(__file__).resolve().parents[4] / "deploy"


def _pid_alive(pid: int) -> bool:
    if sys.platform == "win32":
        import subprocess  # noqa: PLC0415

        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True, check=False).stdout
        return str(pid) in out
    import os  # noqa: PLC0415

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _mk_cell(root: Path, sub: str | None, name: str | None, runtimes=("sim",), programs=True, body=None):
    base = root if sub is None else root / sub
    base.mkdir(parents=True, exist_ok=True)
    text = body if body is not None else (f"cell_type: t@0.1\nname: {name}\nresources: {{}}\n" if name else "cell_type: t@0.1\nresources: {}\n")
    (base / "cell.yaml").write_text(text, encoding="utf-8")
    if runtimes:
        (base / "runtime").mkdir(exist_ok=True)
        for r in runtimes:
            (base / "runtime" / f"{r}.yaml").write_text("active_sources: {}\n", encoding="utf-8")
    if programs:
        (base / "programs").mkdir(exist_ok=True)


def test_scan_cells(tmp_path):
    _mk_cell(tmp_path, None, "Robot", runtimes=("default", "sim"))
    _mk_cell(tmp_path, "washer", "Ecoclean", runtimes=("sim", "live"), programs=False)
    _mk_cell(tmp_path, "broken", None, body="- not: a mapping\n")
    (tmp_path / "logs").mkdir()  # a dir without cell.yaml is ignored
    cells = {c.id: c for c in scan_cells(tmp_path)}
    assert set(cells) == {"default", "washer", "broken"}
    assert cells["default"].name == "Robot" and sorted(cells["default"].runtimes) == ["default", "sim"]
    assert cells["default"].programs is not None
    assert cells["washer"].name == "Ecoclean" and cells["washer"].programs is None
    assert cells["broken"].error is not None and cells["broken"].name == "broken"


def test_shipped_deploy_tree_lists_both_cells():
    cells = {c.id: c for c in scan_cells(DEPLOY)}
    assert cells["default"].name == "dev-cell" and "sim" in cells["default"].runtimes
    assert cells["ecoclean"].name == "ecoclean" and set(cells["ecoclean"].runtimes) >= {"sim", "live"}
    assert cells["ecoclean"].programs.endswith("programs")


@pytest.fixture
def api(tmp_path):
    _mk_cell(tmp_path, None, "Robot", runtimes=("default", "sim"))
    _mk_cell(tmp_path, "washer", "Ecoclean", runtimes=("sim",))
    manager = SupervisorManager(
        str(tmp_path), supervisor_argv=[sys.executable, "-c", "import time\nwhile True: time.sleep(0.1)"],
    )
    client = TestClient(create_app(manager))
    yield client, manager, tmp_path
    manager.close()


def test_activate_switch_stop_and_persist(api):
    client, manager, root = api
    body = client.get("/cells").json()
    assert [c["id"] for c in body["cells"]] == ["default", "washer"] and body["active"] is None

    r = client.post("/cells/default/activate", json={})
    assert r.status_code == 200, r.text
    st = r.json()
    assert st["active"]["cell"] == "default" and st["active"]["runtime"] == "default" and st["alive"]
    pid1 = client.get("/health").json()["pid"]
    assert (root / "host.yaml").read_text().strip().startswith("active:")
    assert manager.restore() == {"cell": "default", "runtime": "default"}

    r = client.post("/cells/washer/activate", json={"runtime": "sim"})
    assert r.status_code == 200
    st = r.json()
    assert st["active"]["cell"] == "washer" and st["alive"]
    pid2 = client.get("/health").json()["pid"]
    assert pid2 != pid1
    # the previous child is gone
    time.sleep(0.2)
    assert not _pid_alive(pid1)

    assert client.post("/cells/washer/activate", json={"runtime": "nope"}).status_code == 404
    assert client.post("/cells/ghost/activate", json={}).status_code == 404

    st = client.post("/cells/stop").json()
    assert st["active"] is None and not st["alive"]
    assert manager.restore() is None
    assert client.get("/cells/active").json() == {"active": None, "alive": False}
