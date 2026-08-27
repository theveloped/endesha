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


def supervisor_log(realm: str, service: str, node: str = "main") -> str:
    """``{realm}/supervisor/{node}/log/{service}`` — one captured stdout/stderr
    line of a supervised child: ``{t, level, stream, source, message}``.
    The same key is queryable for the ring buffer: ``{lines: [...]}``."""
    return key(supervisor_prefix(realm, node), "log", service)


def supervisor_log_glob(realm: str, node: str = "main") -> str:
    """All services' log keys (subscribe/query them in one go)."""
    return key(supervisor_prefix(realm, node), "log", "*")


def supervisor_events(realm: str, node: str = "main") -> str:
    """``{realm}/supervisor/{node}/events`` — lifecycle event stream
    (``{t, kind, service, ...}``); queryable for the ring: ``{events: [...]}``."""
    return key(supervisor_prefix(realm, node), "events")
