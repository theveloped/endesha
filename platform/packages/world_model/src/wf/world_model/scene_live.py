"""Dynamic scene layer over the static config scene (mirrors :mod:`frames_live`).

Producers publish latest-wins ``{realm}/scene/{name}`` objects; a
:class:`LiveSceneList` keeps a live in-memory view and merges those runtime
objects with the static ``config/scene/**`` objects, so the collision preflight
sees a config object and a product-swapped runtime object identically. A live
object shadows a static of the same name.

Unlike :class:`~wf.world_model.frames_live.LiveFrameTree`, scene objects form no
tree, so ``snapshot()`` needs no validation/drop pass: an object whose ``frame``
is unresolved is already skipped by ``collision._build_scene``.

The runtime key is pub-only and NOT GET-able, so the view must be
subscriber-backed and held (seeded once from config), not a per-goal GET merge.
"""

from __future__ import annotations

import threading

from wf.core import keys
from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.core.scene import SceneObject

from .validate import _static_scene_defs

_log = get_logger("wf.world_model.scene_live")


def publish_scene_object(
    session, realm: str, name: str, obj: SceneObject
) -> None:
    """Publish a latest-wins runtime scene object to ``{realm}/scene/{name}``."""
    session.put(keys.dynamic_scene(realm, name), encode(obj.to_wire()))


def delete_scene_object(session, realm: str, name: str) -> None:
    """Remove a runtime scene object via an empty-payload tombstone.

    zenoh latest-wins has no native unset; the live-scene subscriber treats an
    empty/geometry-less payload as a delete.
    """
    session.put(keys.dynamic_scene(realm, name), encode({}))


class LiveSceneList:
    """Static config scene objects plus a live dynamic layer; live shadows config.

    The subscriber thread writes via :meth:`update` while accept/tick threads
    read via :meth:`snapshot`.
    """

    def __init__(self, static: dict[str, SceneObject]):
        self._static = dict(static)
        self._dynamic: dict[str, SceneObject] = {}
        self._lock = threading.Lock()

    def update(self, name: str, obj: SceneObject | None) -> None:
        """Upsert (``obj``) or remove (``None``) a runtime scene object."""
        with self._lock:
            if obj is None:
                self._dynamic.pop(name, None)
            else:
                self._dynamic[name] = obj

    def set_static(self, static: dict[str, SceneObject]) -> None:
        """Replace the static config layer (the dynamic layer is untouched)."""
        with self._lock:
            self._static = dict(static)

    def refresh_static(self, session, *, timeout_s: float = 2.0) -> None:
        """Re-fetch ``config/scene/**`` and replace the static layer, so a config
        scene edit (e.g. a collision opt-out) reaches a running driver without a
        restart. An empty fetch is ignored."""
        static = _static_scene_defs(session, timeout_s=timeout_s)
        if static:
            self.set_static(static)

    def snapshot(self) -> list[SceneObject]:
        """Merged objects as a list; a live object shadows a static of the same name."""
        with self._lock:
            return list({**self._static, **self._dynamic}.values())


def build_live_scene(session, realm: str, *, timeout_s: float = 2.0):
    """Build a :class:`LiveSceneList` and subscribe to ``{realm}/scene/**``.

    Returns ``(live, subscriber)``; the caller ``undeclare()``s the subscriber
    on shutdown. Malformed objects are skipped.
    """
    live = LiveSceneList(_static_scene_defs(session, timeout_s=timeout_s))
    prefix = f"{keys.realm_prefix(realm)}/scene/"

    def _on_sample(sample) -> None:
        try:
            name = str(sample.key_expr)[len(prefix) :]
            d = decode(sample.payload)
            if not d or "geometry" not in d:
                live.update(name, None)
            else:
                live.update(name, SceneObject.from_wire(d))
        except (ValueError, KeyError, TypeError) as exc:
            _log.debug("skipping malformed runtime scene object: %r", exc)

    subscriber = session.declare_subscriber(
        keys.dynamic_scene_glob(realm), _on_sample
    )
    return live, subscriber
