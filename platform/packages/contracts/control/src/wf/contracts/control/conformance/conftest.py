"""Fixtures for the `control` conformance suite. See package docstring."""

from __future__ import annotations

import json
import os
import time

import pytest
import zenoh


@pytest.fixture(scope="session")
def realm() -> str:
    return os.environ.get("WF_CONF_REALM", "cell")


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
