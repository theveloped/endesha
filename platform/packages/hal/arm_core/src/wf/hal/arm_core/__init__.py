"""WF platform L2 `arm_core`: the shared arm-contract core + backend seam.

``ArmCore`` serves the whole ``arm`` contract against a pluggable
:class:`ArmBackend` (SimArmBackend / AuboBackend / a future ReplayArmBackend).
"""

from .backend import ArmBackend
from .core import ArmCore, pose_from_transform

__all__ = ["ArmBackend", "ArmCore", "pose_from_transform"]
