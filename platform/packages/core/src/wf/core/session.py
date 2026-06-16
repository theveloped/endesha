"""Zenoh session bootstrap (design L0)."""

from __future__ import annotations

import os

import zenoh

from .keys import key, realm_prefix

WF_ZENOH_CONFIG_ENV = "WF_ZENOH_CONFIG"


def open_session(config_path: str | None = None) -> zenoh.Session:
    """Open a zenoh session.

    Resolution order: explicit ``config_path`` -> env ``WF_ZENOH_CONFIG`` ->
    ``zenoh.Config()`` (default peer mode).
    """
    path = config_path or os.environ.get(WF_ZENOH_CONFIG_ENV)
    config = zenoh.Config.from_file(path) if path else zenoh.Config()
    return zenoh.open(config)


def declare_alive(
    session: zenoh.Session, realm: str, contract: str, rid: str
) -> zenoh.LivelinessToken:
    """Declare the liveliness token at ``{realm}/{contract}/{rid}/alive``."""
    return session.liveliness().declare_token(
        key(realm_prefix(realm), contract, rid, "alive")
    )
