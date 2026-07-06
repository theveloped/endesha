"""Shared execute_path goal validation + pose-target resolution.

Used by BOTH the aubo and arm_sim drivers' ``on_accept`` callbacks. Pose
targets (``target: {"pose": {frame, xyz, quat}}``, movej only) are resolved
against the static frame tree at goal acceptance: the solved ``q`` is
injected into the target dict in place (the original pose is kept) and the
full resolution blob is attached as ``goal["_resolution"]`` for the
execution snapshot. ``ExecutePathGoal.from_wire`` reads only
``d["waypoints"]``, so the extra key is wire-invisible to clients.

Rejection-reason taxonomy returned by the drivers' ``on_accept`` (this module
plus the gate's own checks): ``bad_goal:``, ``empty_path``,
``unsupported_waypoint_type``, ``target_outside_limits``, ``frame_unknown:``,
``ik_failure:{i}``, ``collision:{a}|{b}`` (from the §5.10 collision preflight,
see :mod:`wf.world_model.preflight`), ``unsupported_constraint`` (a ``free``
loose-goal block on anything but the last waypoint), ``no_feasible_goal:{i}``
(the gate found no reachable, collision-free sample of a loose goal),
``no_joint_state``, ``safety_stop_active``, ``mirroring``, ``busy``.

A ``free`` block on the LAST waypoint's pose target (see
:class:`wf.contracts.arm.messages.Freedom`) leaves one goal DOF free/ranged.
Such a waypoint is NOT resolved to a single ``q`` here: it is recorded as a
``constrained`` resolution entry (nominal pose + freedom + IK seed) and the
gate samples/prunes it after this returns.

A ``movel`` waypoint (pose target only) resolves the same way as a movej pose
target — the endpoint IK gives seed continuity and reachability — but also
records the goal TCP pose in the base frame under ``cartesian`` so execute can
drive a straight Cartesian line to it. The straight-line path itself (and its
singularity / branch guards) is built at execute time.

A ``movel`` + ``free`` block is a PATH-LOOSE move: one DOF is free along the
whole straight-line path (functional redundancy). It is recorded under
``path_loose`` (goal pose + freedom + goal TCP pose + IK seed); the gate does a
cheap endpoint-feasibility prune (``no_feasible_goal``) and execute runs the
redundancy lattice DP (which may fail with ``path_loose:...`` when no on-branch,
singularity-free corridor exists).
"""

from __future__ import annotations

import numpy as np

from wf.contracts.arm import keys
from wf.contracts.arm.messages import ExecutePathGoal, Freedom, Pose
from wf.core.codec import decode
from wf.core.frames import (
    invert_transform,
    make_transform,
    quaternion_to_rotation_matrix,
    transform_to_xyz_quat,
)
from wf.core.frametree import FrameDef, FrameTree, FrameUnknown
from wf.core.scene import SceneObject

from .fk import UrdfFk
from .ik import solve_ik

TCP_FLANGE = "flange"

_FRAMES_PREFIX = "config/frames/"
_SCENE_PREFIX = "config/scene/"


def fetch_config(session, selector: str, timeout_s: float = 2.0) -> dict[str, dict]:
    """GET ``selector``; every ok reply keyed by its key expression. {} on error."""
    try:
        replies = session.get(selector, timeout=timeout_s)
        out: dict[str, dict] = {}
        for reply in replies:
            if reply.ok is not None:
                out[str(reply.ok.key_expr)] = decode(reply.ok.payload)
        return out
    except Exception:
        return {}


def _static_frame_defs(session, timeout_s: float = 2.0) -> dict[str, FrameDef]:
    """The static ``config/frames/**`` defs, keyed by frame name."""
    raw = fetch_config(session, f"{_FRAMES_PREFIX}**", timeout_s=timeout_s)
    return {k[len(_FRAMES_PREFIX) :]: FrameDef.from_wire(v) for k, v in raw.items()}


def fetch_frame_tree(session, timeout_s: float = 2.0) -> FrameTree:
    """The static tree from ``config/frames/**``; empty tree on no service."""
    return FrameTree(_static_frame_defs(session, timeout_s=timeout_s))


def _static_scene_defs(session, timeout_s: float = 2.0) -> dict[str, SceneObject]:
    """The static ``config/scene/**`` objects, keyed by scene name.

    Malformed entries are skipped (a bad object never blocks acceptance of an
    otherwise-valid goal).
    """
    raw = fetch_config(session, f"{_SCENE_PREFIX}**", timeout_s=timeout_s)
    out: dict[str, SceneObject] = {}
    for k, v in raw.items():
        try:
            out[k[len(_SCENE_PREFIX) :]] = SceneObject.from_wire(v)
        except (ValueError, KeyError, TypeError):
            continue
    return out


def fetch_scene(session, timeout_s: float = 2.0) -> list[SceneObject]:
    """Scene objects from ``config/scene/**``; ``[]`` on no service / empty.

    Each entry decodes into a :class:`SceneObject`; malformed entries are
    skipped (a bad object never blocks acceptance of an otherwise-valid goal).
    """
    return list(_static_scene_defs(session, timeout_s=timeout_s).values())


def fetch_tcp(session, rid: str, name: str, timeout_s: float = 2.0) -> dict | None:
    """TCP def from ``config/arm/{rid}/tcp/{name}``; ``flange`` is built in."""
    if name == TCP_FLANGE:
        return {
            "xyz": [0.0, 0.0, 0.0],
            "quat": [0.0, 0.0, 0.0, 1.0],
            "role": "tool",
            "selectable_as_tcp": True,
        }
    replies = session.get(f"config/arm/{rid}/tcp/{name}", timeout=timeout_s)
    for reply in replies:
        if reply.ok is not None:
            return decode(reply.ok.payload)
    return None


def tcp_transform(tcp_def: dict) -> np.ndarray:
    """``T_flange<-tcp`` from a TCP def's xyz/quat."""
    return make_transform(
        quaternion_to_rotation_matrix(tcp_def["quat"]), tcp_def["xyz"]
    )


def _q_within_limits(
    q: list[float], jmin: list[float], jmax: list[float], margin: float
) -> bool:
    return all(
        jmin[j] + margin - 1e-6 <= v <= jmax[j] - margin + 1e-6
        for j, v in enumerate(q)
    )


def resolve_goal(
    goal: dict,
    *,
    fk: UrdfFk,
    rid: str,
    q_start: list[float],
    jmin: list[float],
    jmax: list[float],
    margin: float,
    tree: FrameTree,
    tcp_name: str,
    tcp_T: np.ndarray,
) -> tuple[str | None, dict | None]:
    """Validate + resolve an execute_path goal dict IN PLACE.

    Returns ``(rejection_reason, resolution)`` — exactly one is None. On
    success every pose target has gained ``target["q"]`` and
    ``goal["_resolution"]`` carries the acceptance-time provenance.
    """
    try:
        parsed = ExecutePathGoal.from_wire(goal)
    except Exception as exc:
        return f"bad_goal: {exc!r}", None
    if not parsed.waypoints:
        return "empty_path", None

    base_frame = keys.base_frame(rid)
    tcp_T_inv = invert_transform(tcp_T)
    seed = list(q_start)
    resolved: list[dict] = []
    frames_used: dict[str, dict] = {}

    for i, wp in enumerate(parsed.waypoints):
        if wp.type not in ("movej", "movel"):
            return "unsupported_waypoint_type", None
        is_movel = wp.type == "movel"
        has_q = "q" in wp.target
        has_pose = "pose" in wp.target
        if has_q == has_pose:
            return "bad_goal: target must have exactly one of q|pose", None
        if is_movel and not has_pose:
            return "bad_goal: movel requires a pose target", None

        wp_wire = goal["waypoints"][i]

        if "free" in wp.target:
            # One DOF free/ranged. Recorded (not resolved to a single q) and
            # deferred: movej -> loose END goal (gate samples/prunes/plans);
            # movel -> path-loose redundancy (execute runs the lattice DP).
            if i != len(parsed.waypoints) - 1:
                return "unsupported_constraint", None
            if not has_pose:
                return "bad_goal: free requires a pose target", None
            try:
                free = Freedom.from_wire(wp.target["free"])
                pose = Pose.from_wire(wp.target["pose"])
            except Exception as exc:
                return f"bad_goal: {exc!r}", None
            try:
                T_base_frame = tree.resolve(pose.frame, base_frame)
            except FrameUnknown as e:
                return f"frame_unknown:{e.frame}", None
            if pose.frame != base_frame:
                for name, node in (
                    tree.chain(pose.frame) | tree.chain(base_frame)
                ).items():
                    frames_used[name] = node.to_wire()
            if is_movel:
                T_base_tcp_target = T_base_frame @ make_transform(
                    quaternion_to_rotation_matrix(pose.quat), pose.xyz
                )
                g_xyz, g_quat = transform_to_xyz_quat(T_base_tcp_target)
                resolved.append(
                    {
                        "type": "movel",
                        "target": wp_wire["target"],
                        "path_loose": {
                            "pose": pose.to_wire(),
                            "free": free.to_wire(),
                            "goal_tcp": {"xyz": g_xyz, "quat": g_quat},
                        },
                        "seed_q": list(seed),
                    }
                )
            else:
                resolved.append(
                    {
                        "type": "movej",
                        "target": wp_wire["target"],
                        "constrained": {
                            "pose": pose.to_wire(),
                            "free": free.to_wire(),
                        },
                        "seed_q": list(seed),
                    }
                )
            continue

        if has_q:
            q = wp.target.get("q")
            if not isinstance(q, list) or len(q) != 6:
                return "target_outside_limits", None
            if not _q_within_limits(q, jmin, jmax, margin):
                return "target_outside_limits", None
            q = [float(v) for v in q]
        else:
            try:
                pose = Pose.from_wire(wp.target["pose"])
            except Exception as exc:
                return f"bad_goal: {exc!r}", None
            try:
                T_base_frame = tree.resolve(pose.frame, base_frame)
            except FrameUnknown as e:
                return f"frame_unknown:{e.frame}", None
            if pose.frame != base_frame:
                for name, node in (
                    tree.chain(pose.frame) | tree.chain(base_frame)
                ).items():
                    frames_used[name] = node.to_wire()
            T_base_tcp_target = T_base_frame @ make_transform(
                quaternion_to_rotation_matrix(pose.quat), pose.xyz
            )
            T_base_flange_target = T_base_tcp_target @ tcp_T_inv
            q = solve_ik(
                fk, T_base_flange_target, seed, jmin, jmax, margin=margin
            )
            if q is None:
                return f"ik_failure:{i}", None
            # IK already clamps inside limits; belt-and-braces check.
            if not _q_within_limits(q, jmin, jmax, margin):
                return "target_outside_limits", None
            wp_wire["target"]["q"] = q
            if is_movel:
                # Record the goal TCP pose in the BASE frame so execute drives a
                # straight Cartesian line to it without re-resolving frames. The
                # endpoint q above (seed continuity + reachability) is kept too.
                g_xyz, g_quat = transform_to_xyz_quat(T_base_tcp_target)
                cartesian_goal = {"goal_tcp": {"xyz": g_xyz, "quat": g_quat}}

        seed = q
        entry = {"type": wp.type, "target": wp_wire["target"], "resolved_q": q}
        if is_movel:
            entry["cartesian"] = cartesian_goal
        resolved.append(entry)

    resolution = {
        "waypoints": resolved,
        "frames_used": frames_used,
        "active_tcp": tcp_name,
    }
    goal["_resolution"] = resolution
    return None, resolution


