"""The ``Camera2dBackend`` seam (RFC step 5).

:class:`~wf.hal.camera2d_core.core.Camera2dCore` serves the whole camera2d
contract (the cmd queryables, the single image-publish path with FrameHeader +
monotonic seq/t_capture + eye-in-hand pose, the status loop, grab-while-
streaming rejection). The hardware-specific acquisition lives behind this
interface: connecting, grabbing one frame, the streaming loop, node-map
configure. A backend produces a :class:`CapturedFrame`; the core stamps + emits.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class CapturedFrame:
    """One acquired, already-encoded frame handed to ``core.publish_frame``."""

    data: bytes  # encoded image bytes (jpeg or raw Bayer)
    w: int
    h: int
    encoding: str
    hw_ts_ns: int  # hardware/source timestamp (end-of-exposure); 0 if none
    exposure_us: float
    gain_db: float
    # Optional world<-optical pose to stamp into the FrameHeader. None (the
    # live default) -> the core uses its eye-in-hand pose from the live flange;
    # a replay source supplies the recorded pose so it is preserved.
    pose: dict | None = None


class Camera2dBackend(ABC):
    """The hardware/source-specific half of a camera2d provider."""

    @abstractmethod
    def start(self, core) -> None:
        """Connect (own retry thread) + start acquisition resources."""

    @abstractmethod
    def shutdown(self) -> None:
        """Stop streaming + release resources."""

    @abstractmethod
    def grab(self, spec) -> CapturedFrame:
        """Produce ONE frame for ``spec`` (a FrameSpec). Raises on error or
        when not connected."""

    @abstractmethod
    def start_stream(self, spec) -> None:
        """Start streaming (a StreamParams) — the backend owns its loop and
        calls ``core.publish_frame`` per frame. Raises if it cannot start."""

    @abstractmethod
    def stop_stream(self) -> None:
        """Stop the stream loop (idempotent)."""

    def active_stream(self):
        """The active StreamParams, or None when not streaming. Single source
        of truth for the 'streaming' state (grab is rejected while non-None)."""
        return None

    def configure(self, cmd) -> None:
        """Apply a ConfigureCmd (exposure/gain/auto/white-balance). Default
        no-op for sources without controllable optics."""

    @abstractmethod
    def status(self) -> dict:
        """``{connected: bool, exposure_us: float|None, gain_db: float|None,
        error: str|None}``. The core adds streaming + achieved rate."""
