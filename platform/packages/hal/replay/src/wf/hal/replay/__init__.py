"""WF platform L2 `replay`: per-device replay providers.

``ReplayArmBackend`` / ``ReplayCameraBackend`` are thin backends on the shared
``ArmCore`` / ``Camera2dCore`` that substitute ONE device's recorded source
stream from an MCAP recording into the active namespace, paced to wall clock
and re-stamped so the twin, collision model, and UI consume it like live data.
Run as ``python -m wf.hal.replay.arm`` or ``python -m wf.hal.replay.camera``.
"""
