"""The `camera2d` contract key space (design §4.1/§4.3)."""

from __future__ import annotations

from wf.core.keys import key, realm_prefix


def prefix(realm: str, cid: str) -> str:
    return key(realm_prefix(realm), "camera2d", cid)


def image(realm: str, cid: str) -> str:
    """The single frame topic — stream AND grab frames publish here."""
    return key(prefix(realm, cid), "image")


def state_status(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "state", "status")


def cmd_configure(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "cmd", "configure")


def cmd_grab(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "cmd", "grab")


def cmd_stream_start(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "cmd", "stream_start")


def cmd_stream_stop(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "cmd", "stream_stop")


def alive(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "alive")


def optical_frame(cid: str) -> str:
    """Name of the camera optical frame: ``camera2d/{cid}/optical``.

    Realm-less frame name (mirrors ``arm.keys.base_frame``); used as
    ``frame_id`` until frames v0 lands.
    """
    return key("camera2d", cid, "optical")
