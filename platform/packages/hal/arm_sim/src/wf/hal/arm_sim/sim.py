"""Pure simulated-arm state (no zenoh, no threads).

:class:`SimArm` holds the joint/IO state; the driver owns all locking and
pacing. Goal validation lives in the shared
``wf.world_model.validate.resolve_goal`` used by both drivers.
"""

from __future__ import annotations

import numpy as np

from wf.contracts.arm import keys
from wf.contracts.arm.messages import DO_BANKS, Pose
from wf.core.frames import rotation_matrix_to_quaternion
from wf.world_model.fk import UrdfFk


def pose_from_transform(T: np.ndarray, frame: str) -> Pose:
    """Pose wire payload from a 4x4 transform expressed in ``frame``."""
    return Pose(
        frame=frame,
        xyz=[float(v) for v in T[:3, 3]],
        quat=rotation_matrix_to_quaternion(T[:3, :3]),
    )


class SimArm:
    """Joint/IO state of the simulated arm. Pure — the driver owns locking/pacing."""

    def __init__(self, fk: UrdfFk, home_q: list[float]):
        self.fk = fk
        self.q = list(home_q)
        self.qd = [0.0] * 6
        self.do_bits = 0  # standard bank, LSB = pin 0
        self.tool_do_bits = 0  # accepted but not surfaced in state/io (aubo parity)
        self.di_bits = 0  # static zeros in v0

    def set_q(self, q: list[float], qd: list[float] | None = None) -> None:
        self.q = list(q)
        self.qd = [0.0] * 6 if qd is None else list(qd)

    def set_do(self, bank: str, pin: int, value: int) -> None:
        if bank not in DO_BANKS:
            raise ValueError(f"bank must be one of {DO_BANKS}, got {bank!r}")
        max_pin = 15 if bank == "standard" else 3
        if not 0 <= pin <= max_pin:
            raise ValueError(f"pin {pin} out of range for bank {bank} (0-{max_pin})")
        if value not in (0, 1):
            raise ValueError(f"value must be 0 or 1, got {value!r}")
        mask = 1 << pin
        if bank == "standard":
            self.do_bits = self.do_bits | mask if value else self.do_bits & ~mask
        else:
            self.tool_do_bits = (
                self.tool_do_bits | mask if value else self.tool_do_bits & ~mask
            )

    def flange_pose(self, rid: str) -> Pose:
        T = self.fk.get_ee_transform(self.q)
        return Pose(
            frame=keys.base_frame(rid),
            xyz=[float(v) for v in T[:3, 3]],
            quat=rotation_matrix_to_quaternion(T[:3, :3]),
        )
