"""WF platform L2: simulated camera HAL (camera2d contract).

Implements the ``camera2d`` contract by rendering — a CPU pinhole projection
of a known calibration target at the eye-in-hand camera pose derived from the
sim arm's ``state/flange``. No GPU/OpenGL: the renderer is pure numpy + cv2 so
it runs headless anywhere the genicam HAL's cv2 already runs.

The render uses NOMINAL ground-truth intrinsics, flange→optical mount, and
target geometry from the cell file — deliberately NOT ``config/.../intrinsics``,
because those are exactly what the intrinsics/hand-eye calibration phases will
later recover and check against this sim's ground truth.

v0: the renderer is a ``cv2`` checkerboard projection — no robot/scene geometry,
a single BGR image, no depth or segmentation. Design §5.4 replaces it with a
``pyrender`` scene-graph render loading the shared glTF (§5.10); roadmap phase 9.
"""
