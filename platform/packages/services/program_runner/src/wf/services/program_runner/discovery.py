"""Program discovery: a directory of Python modules (RFC §3.6).

Each ``*.py`` (not ``_``-prefixed) is imported under a fresh module name; the
program class is ``PROGRAM`` if defined, else the unique :class:`Program`
subclass defined in that module. Import errors never crash the runner: the
catalog lists the entry with ``error`` set so the operator sees why.
"""

from __future__ import annotations

import importlib.util
import itertools
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path

from wf.contracts.program.messages import CatalogEntry
from wf.program import Program

_counter = itertools.count()


@dataclass
class Discovered:
    entry: CatalogEntry
    cls: type[Program] | None


def _load_module(path: Path):
    name = f"wf_programs.{path.stem}_{next(_counter)}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


def _program_class(module, path: Path) -> type[Program]:
    explicit = getattr(module, "PROGRAM", None)
    if explicit is not None:
        if not (isinstance(explicit, type) and issubclass(explicit, Program)):
            raise TypeError("PROGRAM must be a Program subclass")
        return explicit
    candidates = [
        obj
        for obj in vars(module).values()
        if isinstance(obj, type)
        and issubclass(obj, Program)
        and obj is not Program
        and obj.__module__ == module.__name__
    ]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise TypeError(f"{path.name} defines no Program subclass (set PROGRAM = ...)")
    raise TypeError(f"{path.name} defines several Program subclasses; set PROGRAM = ...")


def discover(programs_dir: str | Path) -> list[Discovered]:
    root = Path(programs_dir)
    out: list[Discovered] = []
    if not root.is_dir():
        return out
    for path in sorted(root.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            module = _load_module(path)
            cls = _program_class(module, path)
            info = cls.describe()
            name = cls.program_name or path.stem
            out.append(
                Discovered(
                    CatalogEntry(name=name, roles=info["roles"], params=info["params"],
                                 doc=info["doc"], path=str(path), hmi=info.get("hmi") or {},
                                 graph=info.get("graph") or {}),
                    cls,
                )
            )
        except Exception as exc:  # noqa: BLE001 - surfaced in the catalog
            err = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            out.append(Discovered(CatalogEntry(name=path.stem, path=str(path), error=err), None))
    return out
