"""RtdeStream: 200 Hz joint-state subscriber (lifted from live_robot_rerun).

Owns its own RtdeClient + login, mirroring the reference. The topic carries
``["timestamp", "R1_actual_q", "R1_actual_qd", "R1_actual_current"]`` — the
two extra fields are the inventory §3-mandated extension over the reference.
If the controller build rejects them, the stream falls back to
``timestamp``+``R1_actual_q`` and publishes zeros for qd/tau (one warning).
"""

from __future__ import annotations

import threading
from typing import Callable

from wf.core.log import get_logger

_log = get_logger("wf.hal.aubo_i10.rtde")

_FULL_FIELDS = ["timestamp", "R1_actual_q", "R1_actual_qd", "R1_actual_current"]
_MINIMAL_FIELDS = ["timestamp", "R1_actual_q"]


class RtdeStream:
    """on_sample(controller_ts_s, q, qd, current) per RTDE sample."""

    def __init__(
        self,
        ip: str,
        port: int = 30010,
        hz: int = 200,
        user: str = "aubo",
        password: str = "123456",
        on_sample: Callable[[float, list, list, list], None] | None = None,
    ):
        if on_sample is None:
            raise ValueError("on_sample is required")
        self.ip = ip
        self.port = port
        self.hz = hz
        self.user = user
        self.password = password
        self.on_sample = on_sample
        self._rtde = None
        self._topic = None
        self._minimal = False
        self._warned = False
        self._lock = threading.Lock()

    def start(self) -> None:
        import pyaubo_sdk

        rtde = pyaubo_sdk.RtdeClient()
        rtde.connect(self.ip, self.port)
        if not rtde.hasConnected():
            raise ConnectionError(f"RTDE connection to {self.ip}:{self.port} failed")
        rtde.login(self.user, self.password)
        if not rtde.hasLogined():
            rtde.disconnect()
            raise ConnectionError("RTDE login failed")
        self._rtde = rtde

        # Callback pops in declared field order: popDouble, then
        # popVectorDouble per vector field.
        def full_callback(parser):
            controller_ts = parser.popDouble()
            q = list(parser.popVectorDouble())
            qd = list(parser.popVectorDouble())
            current = list(parser.popVectorDouble())
            self.on_sample(controller_ts, q, qd, current)

        def minimal_callback(parser):
            controller_ts = parser.popDouble()
            q = list(parser.popVectorDouble())
            if not self._warned:
                self._warned = True
                _log.warning(
                    "controller rejected R1_actual_qd/R1_actual_current; "
                    "publishing zeros for qd/tau"
                )
            zeros = [0.0] * len(q)
            self.on_sample(controller_ts, q, zeros, zeros)

        try:
            topic = rtde.setTopic(False, _FULL_FIELDS, self.hz, 0)
            if topic < 0:
                raise RuntimeError(f"setTopic returned {topic}")
            rtde.subscribe(topic, full_callback)
            self._topic = topic
        except Exception as exc:
            _log.warning("full RTDE topic failed (%r); retrying minimal fields", exc)
            self._minimal = True
            topic = rtde.setTopic(False, _MINIMAL_FIELDS, self.hz, 0)
            rtde.subscribe(topic, minimal_callback)
            self._topic = topic
        _log.info(
            "RTDE streaming %s @ %d Hz from %s:%s",
            _MINIMAL_FIELDS if self._minimal else _FULL_FIELDS,
            self.hz,
            self.ip,
            self.port,
        )

    def stop(self) -> None:
        with self._lock:
            rtde, topic = self._rtde, self._topic
            self._rtde = self._topic = None
        if rtde is None:
            return
        try:
            if topic is not None:
                rtde.removeTopic(False, topic)
        except Exception:
            pass
        try:
            rtde.disconnect()
        except Exception:
            pass
