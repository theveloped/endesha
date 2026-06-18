"""Key construction and realm validation for the WF bus."""

from __future__ import annotations

# The operating namespace is a single fixed token: the backend a device is
# served by (live/sim/replay/off) is NOT encoded in the key — a consumer cannot
# tell from a key whether a device is real or simulated, which is what lets one
# session mix sources (RFC §3.1). Whole-session global replay keeps its own
# ``replay/<id>`` namespace.
REALM_DEFAULT = "cell"
_REPLAY_PREFIX = "replay/"


def key(*parts: str) -> str:
    """Join key parts with "/". Raises ValueError on empty parts or embedded "//"."""
    for part in parts:
        if not part:
            raise ValueError("empty key part")
        if "//" in part:
            raise ValueError(f"embedded '//' in key part: {part!r}")
        if part.startswith("/") or part.endswith("/"):
            raise ValueError(f"key part has leading/trailing '/': {part!r}")
    return "/".join(parts)


def realm_prefix(realm: str) -> str:
    """Validate a namespace token: a single non-empty segment (the operating
    namespace, default ``"cell"``) or ``"replay/<nonempty id>"`` for a global
    replay session. The token no longer encodes the backend (RFC §3.1)."""
    if realm.startswith(_REPLAY_PREFIX):
        sid = realm[len(_REPLAY_PREFIX) :]
        if sid and "/" not in sid:
            return realm
    elif realm and "/" not in realm:
        return realm
    raise ValueError(
        f"invalid realm {realm!r}: expected '<namespace>' or 'replay/<id>'"
    )


def dynamic_frame(realm: str, name: str) -> str:
    """``{realm}/frames/{name}`` — a dynamically located frame (design §4.5)."""
    return key(realm_prefix(realm), "frames", name)


def dynamic_frames_glob(realm: str) -> str:
    """``{realm}/frames/**`` — subscribe selector for all dynamic frames."""
    return key(realm_prefix(realm), "frames", "**")


def dynamic_scene(realm: str, name: str) -> str:
    """``{realm}/scene/{name}`` — a runtime scene object (latest-wins)."""
    return key(realm_prefix(realm), "scene", name)


def dynamic_scene_glob(realm: str) -> str:
    """``{realm}/scene/**`` — subscribe selector for all runtime scene objects."""
    return key(realm_prefix(realm), "scene", "**")
