"""Cell registry: what this host can run.

A cell definition is a ``cell.yaml`` at ``<deploy>/cell.yaml`` (id ``default``)
or ``<deploy>/<dir>/cell.yaml`` (id ``<dir>``), with its runtime overlays in a
sibling ``runtime/*.yaml`` (overlay id = file stem) and its programs in a
sibling ``programs/``. Only the *files* are listed here; which one is running
is the manager's business.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_ID = "default"


@dataclass
class CellInfo:
    id: str
    name: str
    cell_type: str | None
    path: str  # cell.yaml (absolute)
    programs: str | None  # programs dir (absolute) or None
    runtimes: dict[str, str] = field(default_factory=dict)  # overlay id -> path
    error: str | None = None  # unparsable cell.yaml: listed, not activatable

    def to_wire(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "cell_type": self.cell_type,
            "path": self.path,
            "programs": self.programs,
            "runtimes": sorted(self.runtimes),
            "error": self.error,
        }


def _read_cell(path: Path, cid: str) -> CellInfo:
    base = path.parent
    runtime_dir = base / "runtime"
    runtimes = {p.stem: str(p.resolve()) for p in sorted(runtime_dir.glob("*.yaml"))} if runtime_dir.is_dir() else {}
    programs = str((base / "programs").resolve()) if (base / "programs").is_dir() else None
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise ValueError("cell.yaml must be a mapping")
        name = raw.get("name") or cid
        cell_type = raw.get("cell_type")
        error = None
    except Exception as exc:  # noqa: BLE001 - surfaced in the listing
        name, cell_type, error = cid, None, f"{type(exc).__name__}: {exc}"
    return CellInfo(id=cid, name=str(name), cell_type=cell_type, path=str(path.resolve()),
                    programs=programs, runtimes=runtimes, error=error)


def scan_cells(deploy_root: str | Path) -> list[CellInfo]:
    root = Path(deploy_root)
    out: list[CellInfo] = []
    if (root / "cell.yaml").is_file():
        out.append(_read_cell(root / "cell.yaml", DEFAULT_ID))
    for sub in sorted(p for p in root.iterdir() if p.is_dir()):
        if (sub / "cell.yaml").is_file():
            out.append(_read_cell(sub / "cell.yaml", sub.name))
    return out
