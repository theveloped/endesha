"""Supervisor contract keys for device inventory and source control."""

from __future__ import annotations

from wf.core.keys import key, realm_prefix


def supervisor_prefix(realm: str, node: str) -> str:
    return key(realm_prefix(realm), "supervisor", node)


def supervisor_alive(realm: str, node: str = "main") -> str:
    """``{realm}/supervisor/{node}/alive`` — supervisor liveliness token."""
    return key(supervisor_prefix(realm, node), "alive")


def supervisor_descriptor(realm: str, node: str = "main") -> str:
    """``{realm}/supervisor/{node}/descriptor`` — process state."""
    return key(supervisor_prefix(realm, node), "descriptor")


def supervisor_devices(realm: str, node: str = "main") -> str:
    """``{realm}/supervisor/{node}/devices`` — device inventory and sources."""
    return key(supervisor_prefix(realm, node), "devices")


def supervisor_cmd_set_source(realm: str, node: str = "main") -> str:
    """Cold-switch one device source using ``{device_id, source}``."""
    return key(supervisor_prefix(realm, node), "cmd", "set_source")
