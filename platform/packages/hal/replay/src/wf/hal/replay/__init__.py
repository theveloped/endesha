"""WF platform L2 `replay`: per-device replay providers.

``ReplayArmBackend`` / ``ReplayCameraBackend`` are thin backends on the shared
``ArmCore`` / ``Camera2dCore`` that substitute ONE device's recorded source
stream (from an MCAP recording) into the active namespace, paced wall-clock and
re-stamped fresh, so the live downstream (vision, twin, collision, UI)
reprocesses it. Run as ``python -m wf.hal.replay.arm`` / ``wf.hal.replay.camera``.
"""
