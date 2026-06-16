"""File-backed config store: frames, poses, and TCP definitions.

Pure (no zenoh): the service layer wires it to queryables. Persistence is
``{root_dir}/store.yaml`` (atomic replace on every write) plus an append-only
``{root_dir}/history.jsonl`` revision log. Stored entries keep the value dict
as written; the service-stamped ``revision``/``t`` live beside it and are
merged into a FLAT dict on reads only.
"""

from __future__ import annotations

import json
import os
import re
import threading

import yaml

from wf.core.frametree import FrameCycle, FrameDef, FrameTree, FrameUnknown
from wf.core.scene import SceneObject
from wf.core.time import now_ns

_FRAMES_PREFIX = "config/frames/"
_POSES_PREFIX = "config/poses/"
_SCENE_PREFIX = "config/scene/"
_INTRINSICS_PREFIX = "config/intrinsics/"
_TCP_RE = re.compile(r"^config/arm/[^/]+/tcp/.+")
_TCP_ROLES = ("tool", "sensor", "virtual")
RESERVED_TCP_NAME = "flange"


def _is_numbers(v, n: int) -> bool:
    return (
        isinstance(v, (list, tuple))
        and len(v) == n
        and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v)
    )


class ConfigStore:
    """In-memory mirror of ``store.yaml`` with validated, revisioned writes."""

    def __init__(self, root_dir: str) -> None:
        self.root_dir = root_dir
        self._store_path = os.path.join(root_dir, "store.yaml")
        self._history_path = os.path.join(root_dir, "history.jsonl")
        self._lock = threading.Lock()  # serializes set() read-modify-write
        self._entries: dict[str, dict] = {}
        if os.path.exists(self._store_path):
            with open(self._store_path, encoding="utf-8") as f:
                self._entries = yaml.safe_load(f) or {}

    def get_matching(self, selector: str) -> dict[str, dict]:
        """Entries matching ``selector``; values FLAT (payload + revision/t).

        ``x/y/**`` matches keys starting ``x/y/``; anything else is an exact
        match. Manual string matching — deliberately no zenoh KeyExpr.
        """
        if selector.endswith("/**"):
            prefix = selector[:-2]  # keeps the trailing "/"
            keys = [k for k in self._entries if k.startswith(prefix)]
        else:
            keys = [selector] if selector in self._entries else []
        out: dict[str, dict] = {}
        for k in keys:
            entry = self._entries[k]
            out[k] = {**entry["value"], "revision": entry["revision"], "t": entry["t"]}
        return out

    def set(self, key: str, value: dict) -> int:
        """Validate, persist, and revision one entry; returns the new revision.

        Raises ValueError with a machine-readable reason: ``invalid_key:``,
        ``bad_frame:``/``unknown_parent:``/``cycle:``, ``bad_pose:``,
        ``bad_tcp:``/``reserved_name:flange``.
        """
        with self._lock:
            self._validate(key, value)
            prev = self._entries.get(key)
            revision = prev["revision"] + 1 if prev is not None else 1
            t = now_ns()
            self._entries[key] = {"value": dict(value), "revision": revision, "t": t}
            self._append_history(
                {
                    "t": t,
                    "key": key,
                    "old": prev["value"] if prev is not None else None,
                    "new": dict(value),
                    "revision": revision,
                }
            )
            self._write_store()
            return revision

    def delete(self, key: str) -> None:
        """Remove one entry; logs a history line with ``new`` None.

        Raises ValueError with a machine-readable reason: ``invalid_key:``
        (unknown family), ``not_found:`` (absent key), ``in_use:<child>``
        (a frame still referenced as another frame's parent).
        """
        with self._lock:
            if self._key_family(key) is None:
                raise ValueError(f"invalid_key:{key}")
            if key not in self._entries:
                raise ValueError(f"not_found:{key}")
            if key.startswith(_FRAMES_PREFIX):
                name = key[len(_FRAMES_PREFIX) :]
                for other in sorted(self._entries):
                    if other == key or not other.startswith(_FRAMES_PREFIX):
                        continue
                    if self._entries[other]["value"].get("parent") == name:
                        raise ValueError(f"in_use:{other[len(_FRAMES_PREFIX) :]}")
            removed = self._entries.pop(key)
            self._append_history(
                {
                    "t": now_ns(),
                    "key": key,
                    "old": removed["value"],
                    "new": None,
                    "revision": None,
                }
            )
            self._write_store()

    # ── validation ───────────────────────────────────────────────────────

    def _key_family(self, key: str) -> str | None:
        """Family of a config key: ``frame``/``pose``/``scene``/``tcp``/
        ``intrinsics`` or None."""
        if key.startswith(_FRAMES_PREFIX) and len(key) > len(_FRAMES_PREFIX):
            return "frame"
        if key.startswith(_POSES_PREFIX) and len(key) > len(_POSES_PREFIX):
            return "pose"
        if key.startswith(_SCENE_PREFIX) and len(key) > len(_SCENE_PREFIX):
            return "scene"
        if key.startswith(_INTRINSICS_PREFIX) and len(key) > len(_INTRINSICS_PREFIX):
            return "intrinsics"
        if _TCP_RE.match(key):
            return "tcp"
        return None

    def _validate(self, key: str, value: dict) -> None:
        if not isinstance(value, dict):
            raise ValueError("bad_value:value must be a dict")
        family = self._key_family(key)
        if family == "frame":
            self._validate_frame(key[len(_FRAMES_PREFIX) :], value)
        elif family == "pose":
            self._validate_pose(value)
        elif family == "scene":
            self._validate_scene(value)
        elif family == "intrinsics":
            self._validate_intrinsics(value)
        elif family == "tcp":
            self._validate_tcp(key.rsplit("/", 1)[-1], value)
        else:
            raise ValueError(f"invalid_key:{key}")

    def _validate_frame(self, name: str, value: dict) -> None:
        if not isinstance(value.get("parent"), str):
            raise ValueError("bad_frame:parent must be a string")
        if not _is_numbers(value.get("xyz"), 3):
            raise ValueError("bad_frame:xyz must be 3 floats")
        if not _is_numbers(value.get("quat"), 4):
            raise ValueError("bad_frame:quat must be 4 floats [qx,qy,qz,qw]")
        frames = {
            k[len(_FRAMES_PREFIX) :]: FrameDef.from_wire(e["value"])
            for k, e in self._entries.items()
            if k.startswith(_FRAMES_PREFIX)
        }
        frames[name] = FrameDef.from_wire(value)
        try:
            FrameTree(frames)
        except FrameCycle as exc:
            raise ValueError(f"cycle:{exc.frame}") from exc
        except FrameUnknown as exc:
            raise ValueError(f"unknown_parent:{exc.frame}") from exc

    def _validate_pose(self, value: dict) -> None:
        if not _is_numbers(value.get("q"), 6):
            raise ValueError("bad_pose:q must be 6 floats")

    def _validate_scene(self, value: dict) -> None:
        try:
            SceneObject.from_wire(value)
        except (KeyError, TypeError) as exc:
            raise ValueError(f"bad_scene:{exc!r}") from exc

    def _validate_intrinsics(self, value: dict) -> None:
        # Pinhole optics + frame size. fx/fy/cx/cy px (float >0); w/h px (int >0).
        for k in ("fx", "fy", "cx", "cy"):
            v = value.get(k)
            if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
                raise ValueError(f"bad_intrinsics:{k} must be a positive number")
        for k in ("w", "h"):
            v = value.get(k)
            if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
                raise ValueError(f"bad_intrinsics:{k} must be a positive int")

    def _validate_tcp(self, name: str, value: dict) -> None:
        if name == RESERVED_TCP_NAME:
            raise ValueError(f"reserved_name:{RESERVED_TCP_NAME}")
        if not _is_numbers(value.get("xyz"), 3):
            raise ValueError("bad_tcp:xyz must be 3 floats")
        if not _is_numbers(value.get("quat"), 4):
            raise ValueError("bad_tcp:quat must be 4 floats [qx,qy,qz,qw]")
        if value.get("role") not in _TCP_ROLES:
            raise ValueError(f"bad_tcp:role must be one of {_TCP_ROLES}")
        if not isinstance(value.get("selectable_as_tcp"), bool):
            raise ValueError("bad_tcp:selectable_as_tcp must be a bool")

    # ── persistence ──────────────────────────────────────────────────────

    def _append_history(self, line: dict) -> None:
        os.makedirs(self.root_dir, exist_ok=True)
        with open(self._history_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")

    def _write_store(self) -> None:
        os.makedirs(self.root_dir, exist_ok=True)
        tmp = self._store_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            yaml.safe_dump(self._entries, f, sort_keys=True)
        os.replace(tmp, self._store_path)
