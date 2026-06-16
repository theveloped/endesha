"""Test helpers: deterministic two-peer zenoh link, no router, no multicast."""

from __future__ import annotations

import json
import socket
from contextlib import contextmanager
from typing import Iterator

import zenoh


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@contextmanager
def linked_sessions() -> Iterator[tuple[zenoh.Session, zenoh.Session]]:
    """Two peer sessions linked over a local TCP endpoint.

    Multicast scouting is disabled so tests are deterministic on Windows.
    Session A listens, session B connects.
    """
    port = _free_port()
    endpoint = f"tcp/127.0.0.1:{port}"

    config_a = zenoh.Config()
    config_a.insert_json5("mode", json.dumps("peer"))
    config_a.insert_json5("scouting/multicast/enabled", "false")
    config_a.insert_json5("listen/endpoints", json.dumps([endpoint]))

    config_b = zenoh.Config()
    config_b.insert_json5("mode", json.dumps("peer"))
    config_b.insert_json5("scouting/multicast/enabled", "false")
    config_b.insert_json5("connect/endpoints", json.dumps([endpoint]))

    session_a = zenoh.open(config_a)
    try:
        session_b = zenoh.open(config_b)
        try:
            yield session_a, session_b
        finally:
            session_b.close()
    finally:
        session_a.close()
