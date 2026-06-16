"""Harvester wrapper for BayerRG GigE cameras (FLIR Blackfly S).

Port of the proven reference code (``live_robot_rerun.py:GigECamera`` +
``aubo_cli.py:_trigger_and_grab`` / configure node writes). Frames stay RAW
here — debayer/encode lives in :mod:`.processing`.
"""

from __future__ import annotations

import numpy as np
from harvesters.core import Harvester

from wf.contracts.camera2d.messages import ConfigureCmd
from wf.core.log import get_logger

_log = get_logger("wf.hal.genicam.camera")


class Camera:
    """One GenTL device: enumeration, acquisition modes, node access."""

    def __init__(self, cti_path: str, serial: str | None = None):
        self._h = Harvester()
        self._h.add_file(cti_path)
        self._h.update()
        infos = self._h.device_info_list
        if serial is None:
            if not infos:
                self._h.reset()
                raise RuntimeError(
                    f"no GigE cameras found via GenTL producer: {cti_path}"
                )
            index = 0
        else:
            serials = [info.serial_number for info in infos]
            if serial not in serials:
                self._h.reset()
                raise RuntimeError(
                    f"camera serial {serial!r} not found "
                    f"(found: {', '.join(serials) or '<none>'})"
                )
            index = serials.index(serial)
        self._ia = self._h.create(index)
        self._started = False
        self._normalize_transport_nodes()
        _log.info(
            "camera open: %d device(s), using index %d (serial=%s)",
            len(infos),
            index,
            infos[index].serial_number,
        )

    def _normalize_transport_nodes(self) -> None:
        """Undo persisted rate/bandwidth clamps at connect.

        Vendor tools persist camera-side throttles (observed on the dev
        camera: ``AcquisitionFrameRate`` pinned at 3 fps and a 17 MB/s
        ``DeviceLinkThroughputLimit`` -> ~3 fps ceiling regardless of the
        requested stream rate). The contract decimates host-side from the
        free-running sensor rate, so the camera must not throttle itself:
        disable the frame-rate clamp and open the link throughput to the
        negotiated link speed (the producer recomputes ``GevSCPD`` from
        it). Exposure/gain/WB stay operator-managed via ``cmd/configure``.
        """
        nm = self.nodemap
        try:
            nm.AcquisitionFrameRateEnable.value = False
        except Exception:
            _log.warning("AcquisitionFrameRateEnable write failed", exc_info=True)
        try:
            nm.DeviceLinkThroughputLimit.value = int(nm.DeviceLinkSpeed.value)
        except Exception:
            _log.warning("DeviceLinkThroughputLimit write failed", exc_info=True)

    @property
    def nodemap(self):
        return self._ia.remote_device.node_map

    # ── acquisition ──────────────────────────────────────────────────────

    def start_continuous(self) -> None:
        try:
            self.nodemap.AcquisitionMode.value = "Continuous"
        except Exception:
            pass
        self._ia.start()
        self._started = True

    def stop_acquisition(self) -> None:
        if self._started:
            try:
                self._ia.stop()
            except Exception:
                pass
            self._started = False

    def fetch_raw(self, timeout: float = 1.0) -> tuple[np.ndarray, int] | None:
        """Fetch one frame in Continuous mode.

        Returns ``(raw_bayer_2d, hw_timestamp_ns)`` or None on fetch timeout.
        The data is copied before the buffer is requeued.
        """
        try:
            buf = self._ia.fetch(timeout=timeout)
        except Exception:
            return None
        try:
            ts_ns = buf.timestamp_ns
            comp = buf.payload.components[0]
            raw = comp.data.reshape(comp.height, comp.width).copy()
        finally:
            buf.queue()
        return raw, ts_ns

    def grab_single(self, timeout: float = 5.0) -> tuple[np.ndarray, int]:
        """SingleFrame trigger: arm, expose once, fetch, disarm.

        Guarantees the returned frame was captured after this call — no
        stale buffers. Raises on any failure.
        """
        try:
            self.nodemap.AcquisitionMode.value = "SingleFrame"
        except Exception:
            pass
        self._ia.start()
        try:
            buf = self._ia.fetch(timeout=timeout)
            try:
                ts_ns = buf.timestamp_ns
                comp = buf.payload.components[0]
                raw = comp.data.reshape(comp.height, comp.width).copy()
            finally:
                buf.queue()
        finally:
            try:
                self._ia.stop()
            except Exception:
                pass
        return raw, ts_ns

    # ── nodes ────────────────────────────────────────────────────────────

    def read_exposure_gain(self) -> tuple[float | None, float | None]:
        try:
            exposure = float(self.nodemap.ExposureTime.value)
        except Exception:
            exposure = None
        try:
            gain = float(self.nodemap.Gain.value)
        except Exception:
            gain = None
        return exposure, gain

    def apply_configure(self, cmd: ConfigureCmd) -> None:
        """Write the GenICam nodes; auto toggles map True -> 'Continuous',
        False -> 'Off'. Setting a manual value forces the auto mode off
        first (mirrors the reference CLI)."""
        nm = self.nodemap
        if cmd.auto_exposure is not None:
            try:
                nm.ExposureAuto.value = "Continuous" if cmd.auto_exposure else "Off"
            except Exception:
                _log.warning("ExposureAuto write failed", exc_info=True)
        if cmd.exposure_us is not None:
            try:
                nm.ExposureAuto.value = "Off"
            except Exception:
                pass
            nm.ExposureTime.value = float(cmd.exposure_us)
        if cmd.auto_gain is not None:
            try:
                nm.GainAuto.value = "Continuous" if cmd.auto_gain else "Off"
            except Exception:
                _log.warning("GainAuto write failed", exc_info=True)
        if cmd.gain_db is not None:
            try:
                nm.GainAuto.value = "Off"
            except Exception:
                pass
            nm.Gain.value = float(cmd.gain_db)
        if cmd.auto_wb is not None:
            try:
                nm.BalanceWhiteAuto.value = "Continuous" if cmd.auto_wb else "Off"
            except Exception:
                _log.warning("BalanceWhiteAuto write failed", exc_info=True)
        if cmd.wb_red is not None or cmd.wb_blue is not None:
            try:
                nm.BalanceWhiteAuto.value = "Off"
            except Exception:
                pass
        if cmd.wb_red is not None:
            nm.BalanceRatioSelector.value = "Red"
            nm.BalanceRatio.value = float(cmd.wb_red)
        if cmd.wb_blue is not None:
            nm.BalanceRatioSelector.value = "Blue"
            nm.BalanceRatio.value = float(cmd.wb_blue)

    def close(self) -> None:
        self.stop_acquisition()
        try:
            self._ia.destroy()
        except Exception:
            pass
        try:
            self._h.reset()
        except Exception:
            pass
        _log.info("camera released")
