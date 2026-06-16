"""The `vision` contract key space (design §4.3)."""

from __future__ import annotations

from wf.core.keys import key, realm_prefix


def prefix(realm: str, pipeline: str) -> str:
    return key(realm_prefix(realm), "vision", pipeline)


def image(realm: str, pipeline: str) -> str:
    """A processor's derived frame topic: ``{realm}/vision/{pipeline}/image``."""
    return key(prefix(realm, pipeline), "image")


def alive(realm: str, pipeline: str) -> str:
    return key(prefix(realm, pipeline), "alive")


def result(realm: str, pipeline: str) -> str:
    """A detector's structured output: ``{realm}/vision/{pipeline}/result`` (pub, DROP)."""
    return key(prefix(realm, pipeline), "result")


def cmd_enable(realm: str, pipeline: str) -> str:
    """Runtime toggle: ``{realm}/vision/{pipeline}/cmd/enable`` (queryable)."""
    return key(prefix(realm, pipeline), "cmd", "enable")
