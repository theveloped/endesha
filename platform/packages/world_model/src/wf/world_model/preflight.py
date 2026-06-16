"""Collision preflight for accepted execute_path goals (design §5.10).

The accept gates call this between a successful ``resolve_goal`` and the
safety-stop check. It delegates to a prebuilt :class:`CollisionModel` (Pinocchio
+ Coal): every resolved waypoint ``q`` is checked against the robot's own links
and the ``config/scene/**`` obstacles, and the first penetrating body pair is
returned as a ``collision:{a}|{b}`` rejection reason. With no scene objects and
a self-collision-free path it stays a no-op (``None``) — identical to the
pre-engine behaviour.
"""

from __future__ import annotations

from wf.core.frametree import FrameTree
from wf.core.scene import SceneObject

from .collision import CollisionModel


def preflight(
    resolution: dict,
    scene: list[SceneObject],
    *,
    model: CollisionModel,
    tree: FrameTree,
    base_frame: str,
) -> str | None:
    """Check the resolved waypoints against the scene; ``None`` if clear.

    Returns a ``collision:{a}|{b}`` rejection reason on the first colliding
    body pair, else ``None``.
    """
    trajectory = [wp["resolved_q"] for wp in resolution["waypoints"]]
    result = model.preflight(trajectory, scene, tree, base_frame)
    if not result["ok"]:
        a, b = result["first_violation"]["pair"]
        return f"collision:{a}|{b}"
    return None
