"""Authority <-> watcher round trip over an in-process zenoh peer session."""

from __future__ import annotations

import time
import uuid

import pytest

from wf.contracts.control import keys
from wf.contracts.control.authority import ControlAuthority
from wf.contracts.control.messages import AcquireControl, ControlAck
from wf.contracts.control.watcher import LeaseWatcher
from wf.core.codec import decode, encode


def _realm() -> str:
    return f"t{uuid.uuid4().hex[:8]}"


def _query(session, key, payload) -> ControlAck:
    for reply in session.get(key, payload=encode(payload), timeout=3.0):
        if reply.ok is not None:
            return ControlAck.from_wire(decode(reply.ok.payload))
    pytest.fail(f"no reply from {key}")


def _wait(pred, timeout_s=3.0) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if pred():
            return True
        time.sleep(0.05)
    return pred()


def test_grant_deny_release_visible_to_watcher():
    zenoh = pytest.importorskip("zenoh")
    session = zenoh.open(zenoh.Config())
    realm = _realm()
    authority = ControlAuthority(session, realm, ttl_s=30.0)
    watcher = LeaseWatcher(session, realm)
    try:
        authority.start()
        watcher.start()
        assert _wait(lambda: watcher.authority_alive), "watcher never saw the authority"
        assert not watcher.holds("a")

        ack = _query(session, keys.cmd_acquire(realm), AcquireControl("a", "alice").to_wire())
        assert ack.ok and ack.owner is not None and ack.owner.client_id == "a"
        assert _wait(lambda: watcher.holds("a"))
        assert not watcher.holds("b")

        denied = _query(session, keys.cmd_acquire(realm), AcquireControl("b", "bob").to_wire())
        assert not denied.ok and denied.error == "held_by:alice"
        assert denied.owner is not None and denied.owner.client_id == "a"

        rel = _query(session, keys.cmd_release(realm), {"client_id": "a"})
        assert rel.ok and rel.owner is None
        assert _wait(lambda: not watcher.holds("a"))
    finally:
        watcher.close()
        authority.close()
        session.close()


def test_late_watcher_learns_owner_by_query():
    zenoh = pytest.importorskip("zenoh")
    session = zenoh.open(zenoh.Config())
    realm = _realm()
    authority = ControlAuthority(session, realm, ttl_s=30.0)
    try:
        authority.start()
        _query(session, keys.cmd_acquire(realm), AcquireControl("a", "alice").to_wire())
        watcher = LeaseWatcher(session, realm)  # subscribed AFTER the grant
        try:
            watcher.start()
            assert _wait(lambda: watcher.holds("a"))
        finally:
            watcher.close()
    finally:
        authority.close()
        session.close()


def test_authority_gone_means_no_lease():
    zenoh = pytest.importorskip("zenoh")
    session = zenoh.open(zenoh.Config())
    realm = _realm()
    authority = ControlAuthority(session, realm, ttl_s=30.0)
    watcher = LeaseWatcher(session, realm)
    try:
        authority.start()
        watcher.start()
        _query(session, keys.cmd_acquire(realm), AcquireControl("a", "alice").to_wire())
        assert _wait(lambda: watcher.holds("a"))
        authority.close()
        assert _wait(lambda: not watcher.authority_alive), "liveliness DELETE not seen"
        assert not watcher.holds("a")
    finally:
        watcher.close()
        authority.close()
        session.close()
