"""The `arm` contract key space (design §4.1/§4.2)."""

from __future__ import annotations

from wf.core.keys import key, realm_prefix


def prefix(realm: str, rid: str) -> str:
    return key(realm_prefix(realm), "arm", rid)


def state_joints(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "state", "joints")


def state_flange(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "state", "flange")


def state_tcp(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "state", "tcp")


def state_io(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "state", "io")


def state_status(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "state", "status")


def cmd_set_do(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "set_do")


def cmd_stop(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "stop")


def cmd_clear_protective_stop(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "clear_protective_stop")


def cmd_set_tcp(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "set_tcp")


def cmd_jog(realm: str, rid: str) -> str:
    """``.../cmd/jog`` — pub/sub hold-to-jog stream (NOT a queryable)."""
    return key(prefix(realm, rid), "cmd", "jog")


def cmd_acquire_control(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "acquire_control")


def cmd_release_control(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "release_control")


def state_control_owner(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "state", "control_owner")


def action_prefix(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "action")


def alive(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "alive")


def base_frame(rid: str) -> str:
    """Name of the arm base frame: ``arm/{rid}/base``."""
    return key("arm", rid, "base")
