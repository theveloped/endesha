"""Conformance tests: control contract, implementation-agnostic; bus-only.

Commands speak the wire-contract envelope; ``state/owner`` is a retained
value answering queries with the identical published payload.
"""

from __future__ import annotations

import uuid

import pytest

from wf.contracts.control import keys
from wf.contracts.control.messages import ERROR_REASONS, ControlOwnerState
from wf.core.codec import decode, encode
from wf.core.envelope import CODES, Reply, request as envelope_request


def _cid() -> str:
    return f"control-conf-{uuid.uuid4().hex[:8]}"


def _acquire(session, realm, cid, user) -> Reply:
    reply = envelope_request(session, keys.cmd_acquire(realm), {"user": user},
                             client_id=cid, timeout_s=5.0)
    if not reply.ok and reply.error.reason == "no_reply":
        pytest.skip("no control authority on the bus")
    if not reply.ok:
        assert reply.error.code in CODES and reply.error.reason in ERROR_REASONS
    return reply


def _release(session, realm, cid) -> Reply:
    return envelope_request(session, keys.cmd_release(realm), {},
                            client_id=cid, timeout_s=5.0)


@pytest.fixture
def lease(session, realm):
    """A held lease for the duration of one test; skips if unavailable."""
    cid = _cid()
    reply = _acquire(session, realm, cid, "control-conformance")
    if not reply.ok:
        pytest.skip(f"control lease unavailable: {reply.error}")
    yield cid
    _release(session, realm, cid)


def test_alive_token(session, realm):
    replies = session.liveliness().get(keys.alive(realm), timeout=3.0)
    assert [r.ok for r in replies if r.ok is not None], "no authority liveliness token"


def test_owner_state_query_is_retained(session, realm):
    """Retained-value rule: the queryable answers the identical payload
    shape the stream publishes (1 Hz keepalive)."""
    for reply in session.get(keys.state_owner(realm), timeout=5.0):
        if reply.ok is not None:
            state = ControlOwnerState.from_wire(decode(reply.ok.payload))
            assert state.t > 0
            return
    pytest.skip("no control authority on the bus")


def test_acquire_renew_release_roundtrip(session, realm, lease):
    cid = lease
    # value is the owner state naming the requester
    granted = _acquire(session, realm, cid, "control-conformance")
    assert granted.ok
    owner = ControlOwnerState.from_wire(granted.value).owner
    assert owner is not None and owner.client_id == cid
    # renewal keeps granted_at
    renewed = _acquire(session, realm, cid, "control-conformance")
    assert renewed.ok
    owner2 = ControlOwnerState.from_wire(renewed.value).owner
    assert owner2 is not None and owner2.granted_at == owner.granted_at


def test_second_client_conflicts(session, realm, lease):
    other = _acquire(session, realm, _cid(), "intruder")
    assert not other.ok
    assert other.error.code == "conflict" and other.error.reason == "held_by"


def test_release_not_holder(session, realm):
    reply = _release(session, realm, _cid())
    if not reply.ok and reply.error.reason == "no_reply":
        pytest.skip("no control authority on the bus")
    assert not reply.ok and reply.error.reason == "not_holder"
    assert reply.error.code == "conflict"


def test_missing_req_id_rejected(session, realm):
    """No legacy dialect: a request without ``req_id`` is ``invalid``."""
    for reply in session.get(
        keys.cmd_acquire(realm),
        payload=encode({"client_id": "legacy", "user": "legacy"}),
        timeout=5.0,
    ):
        if reply.ok is None:
            continue
        wire = decode(reply.ok.payload)
        assert wire["ok"] is False and wire["error"]["code"] == "invalid"
        return
    pytest.skip("no control authority on the bus")


def test_release_resubmission_is_idempotent(session, realm, lease):
    """Same ``req_id`` twice -> the original outcome, not not_holder."""
    cid = lease
    req_id = f"conf-idem-{uuid.uuid4().hex[:8]}"
    first = envelope_request(session, keys.cmd_release(realm), {},
                             client_id=cid, req_id=req_id, timeout_s=5.0)
    second = envelope_request(session, keys.cmd_release(realm), {},
                              client_id=cid, req_id=req_id, timeout_s=5.0)
    assert first.ok and second.ok
    # re-acquire so the fixture's release finds a lease to drop
    _acquire(session, realm, cid, "control-conformance")
