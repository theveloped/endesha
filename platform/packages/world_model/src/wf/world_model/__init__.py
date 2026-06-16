"""World model: kinematics, IK, goal validation, trajectory, collision preflight.

Design §5.10: the shared kinematics + geometry + frame spine consumed by both
arm drivers, the planner, and the UI. It is a core-adjacent L1 package (depends
on ``wf-core`` + ``wf-contracts-arm`` + ``ruckig``) rather than living inside a
device HAL. Robot-specific assets (URDF, mesh, joint limits) stay in their HAL;
``UrdfFk`` takes the URDF path explicitly.
"""
