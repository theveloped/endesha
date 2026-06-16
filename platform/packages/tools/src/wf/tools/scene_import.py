"""Importer sink: write an instantiated object to config OR publish it live.

:func:`apply` takes the bare-name frame/scene dicts from
:func:`wf.core.cad_object.instantiate` and lands them either in the persistent
config store (``config/frames/**``, ``config/scene/**`` via ``config/cmd/set``)
or on the runtime bus (``{realm}/frames/**``, ``{realm}/scene/**``). The same
``FrameDef``/``SceneObject`` wire either way, so no consumer can tell a config
object from a runtime one.

Separate from the CLI arg-plumbing so it is unit-testable without argparse.
"""

from __future__ import annotations

from wf.core.frametree import FrameDef
from wf.core.scene import SceneObject
from wf.core.time import now_ns
from wf.services.config import keys as config_keys
from wf.world_model.frames_live import publish_dynamic_frame
from wf.world_model.scene_live import publish_scene_object

from .wfctl import _query


def _ordered_frames(frames: dict[str, FrameDef]) -> list[tuple[str, FrameDef]]:
    """Parent-before-child order: a frame's parent shares its ``{instance}``
    prefix and is a shorter name, so sorting by segment count then name puts the
    root ahead of children/markers — the config store's ``_validate_frame``
    rejects an unknown parent."""
    return sorted(frames.items(), key=lambda kv: (kv[0].count("/"), kv[0]))


def apply(
    frames: dict[str, FrameDef],
    scene: dict[str, SceneObject],
    *,
    session,
    realm: str,
    mode: str,
) -> list[str]:
    """Land an instantiated object; return error strings (``[]`` = ok).

    ``mode == "config"`` writes via ``config/cmd/set`` (validated, root frame
    first). ``mode == "live"`` publishes to the runtime bus (snapshot views drop
    unresolvable entries, so ordering is a soft preference).
    """
    if mode not in ("config", "live"):
        return [f"bad_mode:{mode!r} (expected 'config' or 'live')"]

    errors: list[str] = []

    if mode == "config":
        for name, fd in _ordered_frames(frames):
            reply = _query(
                session,
                config_keys.cmd_set(),
                {"key": config_keys.frame(name), "value": fd.to_wire()},
            )
            if reply is None:
                errors.append(f"frame {name}: no reply from config/cmd/set")
            elif not reply.get("ok"):
                errors.append(f"frame {name}: {reply.get('error')}")
        for name, so in scene.items():
            reply = _query(
                session,
                config_keys.cmd_set(),
                {"key": config_keys.scene(name), "value": so.to_wire()},
            )
            if reply is None:
                errors.append(f"scene {name}: no reply from config/cmd/set")
            elif not reply.get("ok"):
                errors.append(f"scene {name}: {reply.get('error')}")
        return errors

    # mode == "live"
    from wf.core.frametree import DynamicFrameSample

    t = now_ns()
    for name, fd in _ordered_frames(frames):
        publish_dynamic_frame(
            session,
            realm,
            name,
            DynamicFrameSample(
                t=t,
                parent=fd.parent,
                xyz=fd.xyz,
                quat=fd.quat,
                source=fd.source,
                confidence=1.0,
            ),
        )
    for name, so in scene.items():
        publish_scene_object(session, realm, name, so)
    return errors
