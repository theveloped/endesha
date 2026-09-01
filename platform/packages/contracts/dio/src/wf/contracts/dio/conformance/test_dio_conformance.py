"""Conformance tests: dio contract, implementation-agnostic; bus-only.

Commands speak the wire-contract envelope (``wf.core.envelope``): every
reply carries ``ok`` plus exactly one of ``value``/``error``, error codes
come from the closed enum, reasons from the contract's registered list,
and a request without ``req_id`` is rejected — there is no legacy dialect.
"""

from __future__ import annotations

import os
import time

import pytest

from wf.contracts.dio import keys
from wf.contracts.dio.messages import ERROR_REASONS, ChannelsState, ForceChannel, SetChannel
from wf.core.codec import decode, encode
from wf.core.envelope import CODES, Reply, request as envelope_request

from .conftest import collect_samples


def _query_state(session, realm, dio) -> ChannelsState:
    for reply in session.get(keys.state_channels(realm, dio), timeout=5.0):
        if reply.ok is not None:
            return ChannelsState.from_wire(decode(reply.ok.payload))
    pytest.fail("no reply from dio state/channels")


def _call(session, key, client_id, msg) -> Reply:
    reply = envelope_request(session, key, msg.to_wire(), client_id=client_id, timeout_s=5.0)
    if not reply.ok and reply.error.reason == "no_reply":
        pytest.fail(f"no reply from {key}")
    if not reply.ok:
        assert reply.error.code in CODES
        assert reply.error.reason in ERROR_REASONS
    return reply


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
    """Retained-value rule: querying the key returns the identical payload
    shape the stream publishes (wire-contract RFC §3.1)."""
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


def test_envelope_shape(session, realm, dio, client_id):
    """Raw reply is the envelope: ``ok`` plus exactly one of value/error."""
    req = {"req_id": "conf-shape-1", "client_id": client_id,
           "args": SetChannel("no_such_channel_x", True).to_wire()}
    for reply in session.get(keys.cmd_set(realm, dio), payload=encode(req), timeout=5.0):
        if reply.ok is None:
            continue
        wire = decode(reply.ok.payload)
        assert isinstance(wire, dict) and "ok" in wire
        assert ("value" in wire) != ("error" in wire)
        assert wire["error"]["code"] in CODES
        assert wire["error"]["reason"] in ERROR_REASONS
        return
    pytest.fail("no reply from dio cmd/set")


def test_missing_req_id_rejected(session, realm, dio):
    """No legacy dialect: a request without ``req_id`` is ``invalid``."""
    for reply in session.get(
        keys.cmd_set(realm, dio),
        payload=encode({"channel": "whatever", "value": True}),
        timeout=5.0,
    ):
        if reply.ok is None:
            continue
        wire = decode(reply.ok.payload)
        assert wire["ok"] is False and wire["error"]["code"] == "invalid"
        return
    pytest.fail("no reply from dio cmd/set")


def test_set_input_is_read_only(session, realm, dio, client_id):
    name = _first_input(_query_state(session, realm, dio))
    reply = _call(session, keys.cmd_set(realm, dio), client_id, SetChannel(name, True))
    assert not reply.ok and reply.error.reason == "read_only"
    assert reply.error.code == "invalid"


def test_unknown_channel(session, realm, dio, client_id):
    reply = _call(
        session, keys.cmd_set(realm, dio), client_id, SetChannel("no_such_channel_x", True)
    )
    assert not reply.ok and reply.error.reason == "unknown_channel"
    assert reply.error.code == "not_found"
    assert reply.error.detail == "no_such_channel_x"


def test_set_requires_lease(session, realm, dio):
    name = _first_input(_query_state(session, realm, dio))
    reply = _call(session, keys.cmd_set(realm, dio), "not-the-holder", SetChannel(name, True))
    assert not reply.ok and reply.error.reason == "no_control"
    assert reply.error.code == "conflict"
    outputs = [n for n, cv in _query_state(session, realm, dio).channels.items() if cv.kind in ("do", "ao")]
    if outputs:
        reply = _call(session, keys.cmd_force(realm, dio), "not-the-holder", ForceChannel(outputs[0], True))
        assert not reply.ok and reply.error.reason == "no_control"


def test_resubmission_is_idempotent(session, realm, dio, client_id):
    """Same ``req_id`` twice -> the original outcome, not a re-execution."""
    name = _first_input(_query_state(session, realm, dio))
    args = ForceChannel(name, True).to_wire()
    first = envelope_request(session, keys.cmd_force(realm, dio), args,
                             client_id=client_id, req_id="conf-idem-1", timeout_s=5.0)
    second = envelope_request(session, keys.cmd_force(realm, dio), args,
                              client_id=client_id, req_id="conf-idem-1", timeout_s=5.0)
    try:
        assert first.ok and second.ok
    finally:
        _call(session, keys.cmd_force(realm, dio), client_id, ForceChannel(name, None))


def test_force_input_roundtrip(session, realm, dio, client_id):
    state = _query_state(session, realm, dio)
    name = _first_input(state)
    original = state.channels[name].value
    try:
        assert _call(
            session, keys.cmd_force(realm, dio), client_id, ForceChannel(name, not original)
        ).ok
        cv = _wait_channel(
            session, realm, dio, name, lambda c: c.forced and c.value == (not original)
        )
        assert cv is not None and cv.forced and cv.value == (not original)
    finally:
        assert _call(session, keys.cmd_force(realm, dio), client_id, ForceChannel(name, None)).ok
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
        assert _call(session, keys.cmd_set(realm, dio), client_id, SetChannel(name, not original)).ok
        cv = _wait_channel(session, realm, dio, name, lambda c: c.value == (not original))
        assert cv is not None and cv.value == (not original)
    finally:
        _call(session, keys.cmd_set(realm, dio), client_id, SetChannel(name, original))
