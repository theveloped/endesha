"""Dynamic frame layer over the static tree (design §4.5).

Producers publish latest-wins ``{realm}/frames/{name}`` samples; a
:class:`LiveFrameTree` keeps a live in-memory view and merges those dynamic
frames into the *same* ``dict[str, FrameDef]`` the static config tree resolves,
so a ``{frame: "pallet_1"}`` waypoint or a scene object parented to a detected
frame resolves with no consumer change. :class:`FrameTree` is composed, never
modified — every ``snapshot()`` rebuilds a fresh validated tree.

No time-aware ring buffer / interpolation: every consumer resolves at "now".
The wire sample carries ``t``/``source``/``confidence`` so the vision pipeline
can anchor a detection to a stationary parent at ``t_capture`` and a future
consumer-side staleness check stays purely additive.
"""

from __future__ import annotations

import threading

from wf.core import keys
from wf.core.codec import decode, encode
from wf.core.frametree import (
    DynamicFrameSample,
    FrameCycle,
    FrameDef,
    FrameTree,
    FrameUnknown,
)
from wf.core.log import get_logger

from .validate import _static_frame_defs

_log = get_logger("wf.world_model.frames_live")


def publish_dynamic_frame(
    session, realm: str, name: str, sample: DynamicFrameSample
) -> None:
    """Publish a latest-wins dynamic frame to ``{realm}/frames/{name}``."""
    session.put(keys.dynamic_frame(realm, name), encode(sample.to_wire()))


def delete_dynamic_frame(session, realm: str, name: str) -> None:
    """Remove a dynamic frame via an empty-payload tombstone.

    zenoh latest-wins has no native unset; the live-tree subscriber treats an
    empty/parent-less payload as a delete.
    """
    session.put(keys.dynamic_frame(realm, name), encode({}))


class LiveFrameTree:
    """Static frame defs plus a live dynamic layer, queried on demand.

    Composes :class:`FrameTree`; the subscriber thread writes via
    :meth:`update` while accept/tick threads read via :meth:`snapshot`.
    """

    def __init__(self, static: dict[str, FrameDef]):
        self._static = dict(static)
        self._dynamic: dict[str, FrameDef] = {}
        self._lock = threading.Lock()

    def update(self, name: str, sample: DynamicFrameSample | None) -> None:
        """Upsert (``sample``) or remove (``None``) a dynamic frame."""
        with self._lock:
            if sample is None:
                self._dynamic.pop(name, None)
            else:
                self._dynamic[name] = sample.as_frame_def()

    def set_static(self, static: dict[str, FrameDef]) -> None:
        """Replace the static config layer (the dynamic layer is untouched)."""
        with self._lock:
            self._static = dict(static)

    def refresh_static(self, session, *, timeout_s: float = 2.0) -> None:
        """Re-fetch ``config/frames/**`` and replace the static layer, so a
        UI/config frame edit reaches a running driver without a restart. An
        empty fetch (config-service blip) is ignored, keeping the last good
        layer."""
        static = _static_frame_defs(session, timeout_s=timeout_s)
        if static:
            self.set_static(static)

    def snapshot(self) -> FrameTree:
        """A fresh validated :class:`FrameTree` of static merged with dynamic.

        A dynamic frame shadows a static of the same name (design §4.5). A
        dynamic frame whose parent isn't (yet) known would make
        :class:`FrameTree` construction raise; rather than break every resolve,
        the offending dynamic frame(s) are dropped and construction retried
        (each pass drops >=1, so it terminates). Static frames are never
        dropped — the config store validated them on write.
        """
        with self._lock:
            dynamic = dict(self._dynamic)
        while True:
            merged = {**self._static, **dynamic}
            try:
                return FrameTree(merged)
            except (FrameUnknown, FrameCycle) as exc:
                # FrameUnknown.frame is the *missing* node (often a not-yet-known
                # parent); FrameCycle.frame is a node in the cycle. Drop the
                # dynamic frame(s) implicated: the bad name itself if dynamic,
                # plus any dynamic frame parented to it. Each pass removes >=1
                # dynamic frame, so the loop terminates. A frame whose parent
                # later appears resolves on a subsequent snapshot.
                doomed = {
                    n for n, fd in dynamic.items()
                    if n == exc.frame or fd.parent == exc.frame
                }
                if not doomed:
                    # Implicated node is static (or its static chain) — not
                    # something the dynamic layer can fix; surface it.
                    raise
                for n in doomed:
                    _log.debug("dropping unresolvable dynamic frame %r", n)
                    dynamic.pop(n)


def build_live_tree(session, realm: str, *, timeout_s: float = 2.0):
    """Build a :class:`LiveFrameTree` and subscribe to ``{realm}/frames/**``.

    Returns ``(live, subscriber)``; the caller ``undeclare()``s the subscriber
    on shutdown. Malformed samples are skipped.
    """
    live = LiveFrameTree(_static_frame_defs(session, timeout_s=timeout_s))
    prefix = f"{keys.realm_prefix(realm)}/frames/"

    def _on_sample(sample) -> None:
        try:
            name = str(sample.key_expr)[len(prefix) :]
            d = decode(sample.payload)
            if not d or "parent" not in d:
                live.update(name, None)
            else:
                live.update(name, DynamicFrameSample.from_wire(d))
        except (ValueError, KeyError, TypeError) as exc:
            _log.debug("skipping malformed dynamic frame sample: %r", exc)

    subscriber = session.declare_subscriber(
        keys.dynamic_frames_glob(realm), _on_sample
    )
    return live, subscriber
