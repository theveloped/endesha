"""Conformance tests: dio contract, implementation-agnostic; bus-only."""

from __future__ import annotations

import os
import time

import pytest

from wf.contracts.dio import keys
from wf.contracts.dio.messages import Ack, ChannelsState, ForceChannel, SetChannel
from wf.core.codec import decode, encode

from .conftest import collect_samples


def _query_state(session, realm, dio) -> ChannelsState:
    for reply in session.get(keys.state_channels(realm, dio), timeout=5.0):
        if reply.ok is not None:
            return ChannelsState.from_wire(decode(reply.ok.payload))
    pytest.fail("no reply from dio state/channels")


def _ack(session, key, msg) -> Ack:
    for reply in session.get(key, payload=encode(msg.to_wire()), timeout=5.0):
        if reply.ok is not None:
            return Ack.from_wire(decode(reply.ok.payload))
    pytest.fail(f"no reply from {key}")


def _wait_channel(session, realm, dio, name, predicate, timeout_s=3.0):
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        last = _query_state(session, realm, dio).channels.get(name)
        if last is not None and predicate(last):
            return last
        time.sleep(0.1)
    return last


def _first_input(state: ChannelsState) -> str:
    env = os.environ.get("WF_CONF_DIO_INPUT")
    if env:
        return env
    for name, cv in state.channels.items():
        if cv.kind == "di":
            return name
    pytest.skip("device has no digital input channel")


def test_alive_token(session, realm, dio):
    replies = session.liveliness().get(keys.alive(realm, dio), timeout=3.0)
    assert [r.ok for r in replies if r.ok is not None], "no liveliness token"


def test_state_stream_and_query_agree(session, realm, dio):
    queried = _query_state(session, realm, dio)
    assert queried.channels, "no channels declared"
    samples = collect_samples(
        session, keys.state_channels(realm, dio), duration_s=2.5, min_count=1
    )
    assert samples, "no state/channels sample within 2.5 s (1 Hz keepalive expected)"
    streamed = ChannelsState.from_wire(samples[0])
    assert set(streamed.channels) == set(queried.channels)
    for cv in queried.channels.values():
        assert cv.kind in ("di", "do", "ai", "ao")
        assert isinstance(cv.value, (bool, int, float))


def test_set_input_is_read_only(session, realm, dio, client_id):
    name = _first_input(_query_state(session, realm, dio))
    ack = _ack(session, keys.cmd_set(realm, dio), SetChannel(client_id, name, True))
    assert not ack.ok and ack.error == "read_only"


def test_unknown_channel(session, realm, dio, client_id):
    ack = _ack(
        session, keys.cmd_set(realm, dio), SetChannel(client_id, "no_such_channel_x", True)
    )
    assert not ack.ok and ack.error.startswith("unknown_channel:")


def test_set_requires_lease(session, realm, dio):
    name = _first_input(_query_state(session, realm, dio))
    ack = _ack(session, keys.cmd_set(realm, dio), SetChannel("not-the-holder", name, True))
    assert not ack.ok and ack.error in ("no_control", "read_only")
    outputs = [n for n, cv in _query_state(session, realm, dio).channels.items() if cv.kind in ("do", "ao")]
    if outputs:
        ack = _ack(session, keys.cmd_force(realm, dio), ForceChannel("not-the-holder", outputs[0], True))
        assert not ack.ok and ack.error == "no_control"


def test_force_input_roundtrip(session, realm, dio, client_id):
    state = _query_state(session, realm, dio)
    name = _first_input(state)
    original = state.channels[name].value
    try:
        assert _ack(
            session, keys.cmd_force(realm, dio), ForceChannel(client_id, name, not original)
        ).ok
        cv = _wait_channel(
            session, realm, dio, name, lambda c: c.forced and c.value == (not original)
        )
        assert cv is not None and cv.forced and cv.value == (not original)
    finally:
        assert _ack(session, keys.cmd_force(realm, dio), ForceChannel(client_id, name, None)).ok
    cv = _wait_channel(session, realm, dio, name, lambda c: not c.forced)
    assert cv is not None and not cv.forced


def test_set_output_roundtrip(session, realm, dio, client_id):
    name = os.environ.get("WF_CONF_DIO_OUTPUT")
    if not name:
        pytest.skip("WF_CONF_DIO_OUTPUT not set")
    state = _query_state(session, realm, dio)
    assert state.channels[name].kind == "do", "WF_CONF_DIO_OUTPUT must be a digital output"
    original = bool(state.channels[name].value)
    try:
        assert _ack(session, keys.cmd_set(realm, dio), SetChannel(client_id, name, not original)).ok
        cv = _wait_channel(session, realm, dio, name, lambda c: c.value == (not original))
        assert cv is not None and cv.value == (not original)
    finally:
        _ack(session, keys.cmd_set(realm, dio), SetChannel(client_id, name, original))
