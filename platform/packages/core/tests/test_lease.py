"""ControlLease and fenced producer-lease arbitration."""

from __future__ import annotations

import wf.core.lease as lease_mod
from wf.core.lease import ControlLease, FencedLease


def test_grant_then_holds():
    lease = ControlLease(ttl_s=30.0)
    owner, err = lease.acquire("c1", "alice")
    assert err is None
    assert owner["client_id"] == "c1"
    assert owner["user"] == "alice"
    assert owner["expires_at"] > owner["granted_at"]
    assert lease.holds("c1")
    assert not lease.holds("c2")
    assert lease.owner()["client_id"] == "c1"


def test_renewal_extends_expiry_keeps_granted_at(monkeypatch):
    clock = {"t": 1_000_000_000}
    monkeypatch.setattr(lease_mod, "now_ns", lambda: clock["t"])

    lease = ControlLease(ttl_s=30.0)
    owner1, err = lease.acquire("c1", "alice")
    assert err is None
    granted = owner1["granted_at"]
    exp1 = owner1["expires_at"]

    clock["t"] += 5_000_000_000  # +5 s, still inside the 30 s ttl
    owner2, err = lease.acquire("c1", "alice")
    assert err is None
    assert owner2["granted_at"] == granted, "renewal must keep granted_at"
    assert owner2["expires_at"] > exp1, "renewal must bump expires_at"


def test_second_client_blocked_while_held():
    lease = ControlLease(ttl_s=30.0)
    lease.acquire("c1", "alice")
    owner, err = lease.acquire("c2", "bob")
    assert owner is None
    assert err == "held_by:alice"
    assert lease.holds("c1")
    assert not lease.holds("c2")


def test_expiry_frees_for_next_client(monkeypatch):
    clock = {"t": 1_000_000_000}
    monkeypatch.setattr(lease_mod, "now_ns", lambda: clock["t"])

    lease = ControlLease(ttl_s=30.0)
    lease.acquire("c1", "alice")
    assert lease.holds("c1")

    clock["t"] += 31_000_000_000  # +31 s, past ttl
    assert lease.owner() is None, "expired lease reads as free"
    assert not lease.holds("c1")

    owner, err = lease.acquire("c2", "bob")
    assert err is None
    assert owner["client_id"] == "c2"


def test_release_by_non_owner_is_noop():
    lease = ControlLease(ttl_s=30.0)
    lease.acquire("c1", "alice")
    assert lease.release("c2") is False
    assert lease.holds("c1"), "non-owner release must not free the lease"
    assert lease.release("c1") is True
    assert lease.owner() is None


def test_fenced_lease_renews_epoch_then_increments_after_expiry(monkeypatch):
    clock = {"t": 1_000_000_000}
    monkeypatch.setattr(lease_mod, "now_ns", lambda: clock["t"])
    lease = FencedLease(ttl_s=10.0, authority_id="authority-a")

    first, err = lease.acquire("c1", "alice")
    assert err is None
    assert first["epoch"] == 1
    assert lease.holds("c1", "authority-a", 1)

    clock["t"] += 3_000_000_000
    renewed, err = lease.acquire("c1", "alice")
    assert err is None
    assert renewed["epoch"] == 1
    assert renewed["expires_at"] > first["expires_at"]

    clock["t"] += 11_000_000_000
    second, err = lease.acquire("c2", "bob")
    assert err is None
    assert second["epoch"] == 2
    assert not lease.holds("c1", "authority-a", 1)
    assert lease.holds("c2", "authority-a", 2)


def test_fenced_lease_rejects_wrong_authority_and_epoch():
    lease = FencedLease(authority_id="authority-a")
    lease.acquire("c1", "alice")
    assert not lease.holds("c1", "old-authority", 1)
    assert not lease.holds("c1", "authority-a", 0)
