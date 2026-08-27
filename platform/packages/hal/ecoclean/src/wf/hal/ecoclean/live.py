"""The live Ecoclean: the OPC-UA tags backend pre-loaded with the machine's
inventory and the 0.5 s ``WatchDogExt`` toggle the PLC needs to stay in auto.

Cell params (``sources.live.params``)::

    endpoint: opc.tcp://192.168.0.1:4840
    username: ecoclean
    password: "..."
    timeout_s: 5.0
    subscription_ms: 100
    watchdog: {tag: WatchDogExt, period_s: 0.5}   # default
"""

from __future__ import annotations

from wf.hal.opcua import OpcuaBackend

from . import inventory as inv


def make_live_backend(params: dict) -> OpcuaBackend:
    p = {**params, "inventory": inv.inventory_dict()}
    p.setdefault("watchdog", {"tag": "WatchDogExt", "period_s": 0.5})
    return OpcuaBackend(p)
