"""WF platform L2 HAL for the Aubo i10 (`aubo_driver`).

`pyaubo_sdk` is lazy-imported everywhere so this package imports on machines
without the vendor SDK (CI, conformance hosts).

`BUNDLED_URDF` is the robot-specific URDF asset this HAL owns; the generic
`wf.world_model.fk.UrdfFk` takes it explicitly (the sim arm HAL reuses it).
"""

from pathlib import Path

BUNDLED_URDF = (
    Path(__file__).parent / "assets" / "aubo_description" / "aubo_i10.urdf"
)
