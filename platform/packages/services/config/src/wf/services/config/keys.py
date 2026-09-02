"""Key builders for the realm-less config store (design §4.4).

Config keys carry no realm prefix: they are shared by all realms, so config
traffic is never captured by the recorder's ``{realm}/**`` subscriber.
"""

from __future__ import annotations

from wf.core.keys import key

CONFIG_PREFIX = "config"

#: Registered envelope error ``reason`` values for cmd/set + cmd/delete
#: (wire-contract RFC §5); the store's ValueError heads map 1:1 onto these.
ERROR_REASONS = (
    "bad_request",
    "invalid_key",
    "unknown_key",
    "bad_frame",
    "unknown_parent",
    "cycle",
    "bad_pose",
    "bad_tcp",
    "bad_intrinsics",
    "bad_collision",
    "bad_layout",
    "reserved_name",
    "set_failed",
    "delete_failed",
)


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


def program_pose(program: str, name: str) -> str:
    """``config/programs/{program}/poses/{name}`` — a pose scoped to one program
    (resolved before the cell-wide ``config/poses/{name}``)."""
    return key(CONFIG_PREFIX, "programs", program, "poses", name)


def program_poses_glob(program: str) -> str:
    return key(CONFIG_PREFIX, "programs", program, "poses", "**")


def program_layout(program: str) -> str:
    """``config/programs/{program}/layout`` — node positions of the program's
    state-machine graph view (``{"positions": {state: [x, y]}}``)."""
    return key(CONFIG_PREFIX, "programs", program, "layout")


def programs_glob() -> str:
    return key(CONFIG_PREFIX, "programs", "**")


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
