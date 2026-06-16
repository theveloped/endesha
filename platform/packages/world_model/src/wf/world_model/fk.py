"""URDF forward kinematics (parse, per-link 4x4 transforms).

Ported from the proven reference implementation with one change: scipy
Rotation usage replaced by `wf.core.frames` numpy helpers. The URDF path is
caller-supplied (the robot HAL owns the asset; ``world_model`` carries no
robot-specific default).

The Aubo i10 kinematic chain is:
  base_link -> shoulder_Link -> upperArm_Link -> foreArm_Link
            -> wrist1_Link -> wrist2_Link -> wrist3_Link

All 6 joints are revolute. `get_ee_transform` returns the wrist3_Link (the
*flange* in design naming) pose in the base frame.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

from wf.core.frames import rpy_to_matrix


class UrdfFk:
    """Forward kinematics for a URDF arm (Aubo i10 chain ordering)."""

    JOINT_ORDER = [
        "shoulder_joint",
        "upperArm_joint",
        "foreArm_joint",
        "wrist1_joint",
        "wrist2_joint",
        "wrist3_joint",
    ]

    LINK_ORDER = [
        "base_link",
        "shoulder_Link",
        "upperArm_Link",
        "foreArm_Link",
        "wrist1_Link",
        "wrist2_Link",
        "wrist3_Link",
    ]

    def __init__(self, urdf_path):
        self.urdf_path = Path(urdf_path)
        if not self.urdf_path.exists():
            raise FileNotFoundError(f"URDF not found: {self.urdf_path}")
        self._joints: dict[str, dict] = {}
        self._links: set[str] = set()
        self._parse_urdf()

    def _parse_urdf(self) -> None:
        tree = ET.parse(str(self.urdf_path))
        root = tree.getroot()

        for link_elem in root.findall("link"):
            self._links.add(link_elem.get("name"))

        for joint_elem in root.findall("joint"):
            name = joint_elem.get("name")
            joint_type = joint_elem.get("type")

            parent = joint_elem.find("parent").get("link")
            child = joint_elem.find("child").get("link")

            origin = joint_elem.find("origin")
            xyz = [0.0, 0.0, 0.0]
            rpy = [0.0, 0.0, 0.0]
            if origin is not None:
                if origin.get("xyz"):
                    xyz = [float(v) for v in origin.get("xyz").split()]
                if origin.get("rpy"):
                    rpy = [float(v) for v in origin.get("rpy").split()]

            axis_elem = joint_elem.find("axis")
            axis = [0.0, 0.0, 1.0]  # default Z
            if axis_elem is not None and axis_elem.get("xyz"):
                axis = [float(v) for v in axis_elem.get("xyz").split()]

            self._joints[name] = {
                "type": joint_type,
                "parent": parent,
                "child": child,
                "origin_xyz": np.array(xyz, dtype=np.float64),
                "origin_rpy": np.array(rpy, dtype=np.float64),
                "axis": np.array(axis, dtype=np.float64),
            }

    @staticmethod
    def _rpy_to_matrix(rpy) -> np.ndarray:
        """Roll-pitch-yaw (extrinsic XYZ) -> 4x4 transform."""
        T = np.eye(4, dtype=np.float64)
        T[:3, :3] = rpy_to_matrix(rpy)
        return T

    @staticmethod
    def _translation_matrix(xyz) -> np.ndarray:
        T = np.eye(4, dtype=np.float64)
        T[:3, 3] = xyz
        return T

    @staticmethod
    def _rotation_about_axis(axis, angle) -> np.ndarray:
        """4x4 rotation about an arbitrary axis (Rodrigues)."""
        axis = np.asarray(axis, dtype=np.float64)
        x, y, z = axis / np.linalg.norm(axis)
        c = math.cos(angle)
        s = math.sin(angle)
        omc = 1.0 - c
        R = np.array(
            [
                [c + x * x * omc, x * y * omc - z * s, x * z * omc + y * s],
                [y * x * omc + z * s, c + y * y * omc, y * z * omc - x * s],
                [z * x * omc - y * s, z * y * omc + x * s, c + z * z * omc],
            ],
            dtype=np.float64,
        )
        T = np.eye(4, dtype=np.float64)
        T[:3, :3] = R
        return T

    def compute_fk(self, joint_angles) -> dict[str, np.ndarray]:
        """Per-link 4x4 transforms in the base_link frame (base = identity)."""
        joint_angles = np.asarray(joint_angles, dtype=np.float64)
        if joint_angles.shape != (6,):
            raise ValueError(f"Expected 6 joint angles, got {joint_angles.shape}")

        link_transforms = {"base_link": np.eye(4, dtype=np.float64)}
        current_transform = np.eye(4, dtype=np.float64)

        for i, joint_name in enumerate(self.JOINT_ORDER):
            joint = self._joints[joint_name]
            angle = joint_angles[i]

            T_origin = self._translation_matrix(
                joint["origin_xyz"]
            ) @ self._rpy_to_matrix(joint["origin_rpy"])
            T_joint = self._rotation_about_axis(joint["axis"], angle)

            current_transform = current_transform @ T_origin @ T_joint
            link_transforms[joint["child"]] = current_transform.copy()

        return link_transforms

    def get_joint_limits(self) -> dict[str, tuple[float, float]]:
        """Joint limits from the URDF: joint_name -> (lower, upper) rad."""
        tree = ET.parse(str(self.urdf_path))
        root = tree.getroot()
        limits = {}
        for joint_elem in root.findall("joint"):
            name = joint_elem.get("name")
            limit_elem = joint_elem.find("limit")
            if limit_elem is not None:
                lower = float(limit_elem.get("lower", "-3.14"))
                upper = float(limit_elem.get("upper", "3.14"))
                limits[name] = (lower, upper)
        return limits

    def get_ee_transform(self, joint_angles) -> np.ndarray:
        """4x4 transform of wrist3_Link (the flange) in the base frame."""
        return self.compute_fk(joint_angles)["wrist3_Link"]
