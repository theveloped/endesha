"""Key construction and realm validation for the WF bus."""

from __future__ import annotations

REALM_LIVE = "live"
REALM_SIM = "sim"
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
    """Validate a realm name: "live" | "sim" | "replay/<nonempty id>"."""
    if realm in (REALM_LIVE, REALM_SIM):
        return realm
    if realm.startswith(_REPLAY_PREFIX) and len(realm) > len(_REPLAY_PREFIX):
        return realm
    raise ValueError(
        f"invalid realm {realm!r}: expected 'live', 'sim', or 'replay/<id>'"
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
