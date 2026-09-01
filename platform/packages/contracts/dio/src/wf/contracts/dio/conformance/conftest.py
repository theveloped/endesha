"""Fixtures for the `dio` conformance suite. See package docstring for env."""

from __future__ import annotations

import json
import os
import time
import uuid

import pytest
import zenoh

from wf.contracts.control import keys as control_keys
from wf.core.codec import decode
from wf.core.envelope import request as envelope_request


@pytest.fixture(scope="session")
def realm() -> str:
    return os.environ.get("WF_CONF_REALM", "cell")


@pytest.fixture(scope="session")
def dio() -> str:
    return os.environ.get("WF_CONF_DIO", "io0")


@pytest.fixture(scope="session")
def session():
    endpoint = os.environ.get("WF_CONF_CONNECT")
    if not endpoint:
        pytest.skip("WF_CONF_CONNECT not set")
    config = zenoh.Config()
    config.insert_json5("mode", json.dumps("client"))
    config.insert_json5("scouting/multicast/enabled", "false")
    config.insert_json5("connect/endpoints", json.dumps([endpoint]))
    s = zenoh.open(config)
    time.sleep(0.5)
    yield s
    s.close()


@pytest.fixture(scope="session")
def client_id(session, realm) -> str:
    """Hold the cell control lease for the whole suite."""
    cid = f"dio-conf-{uuid.uuid4().hex[:8]}"
    reply = envelope_request(session, control_keys.cmd_acquire(realm),
                             {"user": "dio-conformance"}, client_id=cid, timeout_s=5.0)
    if not reply.ok and reply.error.reason == "no_reply":
        pytest.skip("no control authority on the bus")
    if not reply.ok:
        pytest.skip(f"control lease unavailable: {reply.error}")
    yield cid
    envelope_request(session, control_keys.cmd_release(realm), {},
                     client_id=cid, timeout_s=5.0)


def collect_samples(session, key: str, *, duration_s: float, min_count: int = 0):
    samples: list[dict] = []
    sub = session.declare_subscriber(key, lambda s: samples.append(decode(s.payload)))
    try:
        deadline = time.monotonic() + duration_s
        while time.monotonic() < deadline:
            time.sleep(0.05)
            if min_count and len(samples) >= min_count:
                break
        return list(samples)
    finally:
        sub.undeclare()
