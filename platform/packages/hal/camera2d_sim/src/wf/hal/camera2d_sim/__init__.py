"""WF platform L2: camera2d sim package — frame utilities + render-block config.

The pyrender-based sim driver/renderer were retired: the live sim camera is now
the external headless-browser HAL (a stripped Three.js twin build rendered under
headless Chromium, see deploy/Dockerfile.headless), and cam0 is ``hal: external``
in cell.sim.yaml. What remains here are the still-used pure utilities:

- ``processing`` — cv2/numpy frame path (JPEG encode + BayerRG8 mosaic) shared
  by the camera2d frame contract and the vision tests; the raw-encoding
  reference for downstream consumers.
- ``config`` — the ``render`` block schema loader (nominal intrinsics, mount,
  target geometry) merged with defaults.
"""
