"""Service-level tests over a real zenoh peer link (no router).

Covers the publish-on-change behaviour: a ``config/cmd/set`` republishes the new
value on its own key and ``config/cmd/delete`` republishes an empty tombstone, so
live subscribers (e.g. the sim camera page) track edits without re-GETting.
"""

from __future__ import annotations

import time

import pytest

from wf.core.codec import decode, encode
from wf.core.envelope import request as envelope_request
from wf.core.testing import linked_sessions
from wf.services.config import keys
from wf.services.config.service import ConfigService
from wf.services.config.store import ConfigStore

SCENE = {
    "frame": "table",
    "pose": {"xyz": [0.0, 0.0, -0.025], "quat": [0.0, 0.0, 0.0, 1.0]},
    "geometry": {"type": "box", "size": [0.8, 0.8, 0.05]},
    "meta": {},
}


@pytest.fixture
def linked():
    with linked_sessions() as (session_a, session_b):
        yield session_a, session_b


def _query(session, key: str, payload: dict, timeout_s: float = 5.0) -> dict | None:
    replies = session.get(key, payload=encode(payload), timeout=timeout_s)
    for reply in replies:
        if reply.ok is not None:
            return decode(reply.ok.payload)
    return None


def _wait_until(predicate, timeout_s: float, message: str) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(message)


def test_cmd_set_and_delete_publish_on_key(linked, tmp_path):
    session_a, session_b = linked
    service = ConfigService(session_b, ConfigStore(str(tmp_path)))
    service.start()
    time.sleep(0.5)  # queryable/route propagation

    received: list[tuple[str, bytes]] = []
    sub = session_a.declare_subscriber(
        keys.scene_glob(),
        lambda s: received.append((str(s.key_expr), s.payload.to_bytes())),
    )
    time.sleep(0.3)  # subscriber propagation

    try:
        # set -> publishes the value on its own key
        reply = envelope_request(
            session_a, keys.cmd_set(), {"key": keys.scene("foo"), "value": SCENE}
        )
        assert reply.ok, reply.error
        _wait_until(lambda: len(received) >= 1, 5.0, "no set sample published")
        key, payload = received[-1]
        assert key == keys.scene("foo")
        # The published sample is the STORED value in the same flat form a
        # query returns (value + revision/t), so subscribers and queriers agree.
        published = decode(payload)
        assert published["revision"] == 1 and published["t"] > 0
        assert {k: v for k, v in published.items() if k not in ("revision", "t")} == SCENE

        # delete -> publishes an empty tombstone on the same key
        reply = envelope_request(session_a, keys.cmd_delete(), {"key": keys.scene("foo")})
        assert reply.ok, reply.error
        _wait_until(lambda: len(received) >= 2, 5.0, "no delete tombstone published")
        key, payload = received[-1]
        assert key == keys.scene("foo")
        assert decode(payload) == {}
    finally:
        sub.undeclare()
        service.shutdown()
