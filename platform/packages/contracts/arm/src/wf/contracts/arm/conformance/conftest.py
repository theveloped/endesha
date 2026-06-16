"""Fixtures for the `arm` conformance suite. See package docstring for env."""

from __future__ import annotations

import json
import os
import time

import pytest
import zenoh

from wf.core.codec import decode


@pytest.fixture(scope="session")
def realm() -> str:
    return os.environ.get("WF_CONF_REALM", "live")


@pytest.fixture(scope="session")
def rid() -> str:
    return os.environ.get("WF_CONF_RID", "r1")


@pytest.fixture(scope="session")
def session():
    endpoint = os.environ.get("WF_CONF_CONNECT")
    if not endpoint:
        pytest.skip("WF_CONF_CONNECT not set")
    config = zenoh.Config()
    config.insert_json5("mode", json.dumps("peer"))
    config.insert_json5("scouting/multicast/enabled", "false")
    config.insert_json5("connect/endpoints", json.dumps([endpoint]))
    s = zenoh.open(config)
    # Give routes a moment to propagate before the first assertion.
    time.sleep(0.5)
    yield s
    s.close()


def collect_samples(session, key: str, *, duration_s: float, min_count: int = 0):
    """Collect decoded payloads from `key` for `duration_s` seconds."""
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


def first_sample(session, key: str, *, timeout_s: float) -> dict:
    """Block for the first decoded payload on `key`; fail the test on timeout."""
    samples = collect_samples(session, key, duration_s=timeout_s, min_count=1)
    if not samples:
        pytest.fail(f"no sample on {key} within {timeout_s}s")
    return samples[0]
