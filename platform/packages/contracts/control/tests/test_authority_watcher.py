"""Authority <-> watcher round trip over an in-process zenoh peer session."""

from __future__ import annotations

import time
import uuid

import pytest

from wf.contracts.control import keys
from wf.contracts.control.authority import ControlAuthority
from wf.contracts.control.messages import ControlOwnerState
from wf.contracts.control.watcher import LeaseWatcher
from wf.core.envelope import Reply, request as envelope_request


def _realm() -> str:
    return f"t{uuid.uuid4().hex[:8]}"


def _acquire(session, realm, cid, user) -> Reply:
    return envelope_request(session, keys.cmd_acquire(realm), {"user": user},
                            client_id=cid, timeout_s=3.0)


def _release(session, realm, cid) -> Reply:
    return envelope_request(session, keys.cmd_release(realm), {},
                            client_id=cid, timeout_s=3.0)


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

        ack = _acquire(session, realm, "a", "alice")
        assert ack.ok
        granted = ControlOwnerState.from_wire(ack.value)
        assert granted.owner is not None and granted.owner.client_id == "a"
        assert _wait(lambda: watcher.holds("a"))
        assert not watcher.holds("b")

        denied = _acquire(session, realm, "b", "bob")
        assert not denied.ok
        assert denied.error.code == "conflict" and denied.error.reason == "held_by"
        assert denied.error.detail == "alice"

        rel = _release(session, realm, "a")
        assert rel.ok and ControlOwnerState.from_wire(rel.value).owner is None
        not_holder = _release(session, realm, "a")
        assert not not_holder.ok and not_holder.error.reason == "not_holder"
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
        _acquire(session, realm, "a", "alice")
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
        _acquire(session, realm, "a", "alice")
        assert _wait(lambda: watcher.holds("a"))
        authority.close()
        assert _wait(lambda: not watcher.authority_alive), "liveliness DELETE not seen"
        assert not watcher.holds("a")
    finally:
        watcher.close()
        authority.close()
        session.close()
