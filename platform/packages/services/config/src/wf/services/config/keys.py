"""Key builders for the realm-less config store (design §4.4).

Config keys carry no realm prefix: they are shared by all realms, so config
traffic is never captured by the recorder's ``{realm}/**`` subscriber.
"""

from __future__ import annotations

from wf.core.keys import key

CONFIG_PREFIX = "config"


def frame(name: str) -> str:
    """``config/frames/{name}`` — name may contain ``/``."""
    return key(CONFIG_PREFIX, "frames", name)


def frames_glob() -> str:
    return key(CONFIG_PREFIX, "frames", "**")


def pose(name: str) -> str:
    return key(CONFIG_PREFIX, "poses", name)


def poses_glob() -> str:
    return key(CONFIG_PREFIX, "poses", "**")


def scene(name: str) -> str:
    """``config/scene/{name}`` — name may contain ``/``."""
    return key(CONFIG_PREFIX, "scene", name)


def scene_glob() -> str:
    return key(CONFIG_PREFIX, "scene", "**")


def tcp(rid: str, name: str) -> str:
    return key(CONFIG_PREFIX, "arm", rid, "tcp", name)


def tcps_glob(rid: str) -> str:
    return key(CONFIG_PREFIX, "arm", rid, "tcp", "**")


def intrinsics(cid: str) -> str:
    """``config/intrinsics/{cid}`` — camera optical intrinsics + frame size."""
    return key(CONFIG_PREFIX, "intrinsics", cid)


def intrinsics_glob() -> str:
    return key(CONFIG_PREFIX, "intrinsics", "**")


def collision_disabled_pairs(rid: str) -> str:
    """``config/arm/{rid}/collision/disabled_pairs`` — declared collision
    exceptions (SRDF ``disable_collisions``): ``{pairs: [{a, b, reason?}]}``."""
    return key(CONFIG_PREFIX, "arm", rid, "collision", "disabled_pairs")


def cmd_set() -> str:
    return key(CONFIG_PREFIX, "cmd", "set")


def cmd_delete() -> str:
    return key(CONFIG_PREFIX, "cmd", "delete")


def alive() -> str:
    return key(CONFIG_PREFIX, "alive")
