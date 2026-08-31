"""QueryAudit: handled queries are echoed as samples on {realm}/audit/{svc}."""

from __future__ import annotations

import time

import pytest

from wf.core.audit import QueryAudit, audit_key
from wf.core.codec import decode, encode
from wf.core.testing import linked_sessions


@pytest.fixture
def linked():
    with linked_sessions() as (server, client):
        yield server, client


def _first_reply(replies):
    for r in replies:
        if r.ok is not None:
            return decode(r.ok.payload)
    return None


def test_audit_echoes_query_and_reply(linked):
    server, client = linked
    audit = QueryAudit(server, "cellx", "config")

    def handler(query):
        req = decode(query.payload)
        query.reply(str(query.key_expr), encode({"ok": True, "echo": req["value"]}))

    queryable = server.declare_queryable("config/cmd/set", audit.wrap(handler))
    records: list[dict] = []
    sub = client.declare_subscriber(audit_key("cellx", "config"), lambda s: records.append(decode(s.payload)))
    time.sleep(0.3)

    reply = _first_reply(client.get("config/cmd/set", payload=encode({"key": "k", "value": 7}), timeout=5.0))
    assert reply == {"ok": True, "echo": 7}

    deadline = time.time() + 5.0
    while time.time() < deadline and not records:
        time.sleep(0.05)
    assert len(records) == 1
    rec = records[0]
    assert rec["service"] == "config"
    assert rec["key"] == "config/cmd/set"
    assert rec["request"] == {"key": "k", "value": 7}
    assert rec["reply"] == {"ok": True, "echo": 7}
    assert rec["ok"] is True
    assert rec["duration_ms"] >= 0
    sub.undeclare()
    queryable.undeclare()


def test_audit_key_serves_history(linked):
    """The audit key is queryable: late joiners get the ring of past echoes."""
    server, client = linked
    audit = QueryAudit(server, "cellx", "hist", maxlen=3)

    def handler(query):
        query.reply(str(query.key_expr), encode({"ok": True}))

    queryable = server.declare_queryable("cellx/hist/cmd", audit.wrap(handler))
    time.sleep(0.3)
    for i in range(5):
        _first_reply(client.get("cellx/hist/cmd", payload=encode({"n": i}), timeout=5.0))
    time.sleep(0.2)

    history = _first_reply(client.get(audit_key("cellx", "hist"), timeout=5.0))
    assert history is not None
    records = history["records"]
    assert [r["request"]["n"] for r in records] == [2, 3, 4]  # ring keeps the last 3
    assert all(r["service"] == "hist" and r["ok"] is True for r in records)
    audit.close()
    queryable.undeclare()


def test_audit_marks_handler_errors(linked):
    server, client = linked
    audit = QueryAudit(server, "cellx", "boom")

    def handler(query):
        raise RuntimeError("kaput")

    queryable = server.declare_queryable("cellx/boom/cmd", audit.wrap(handler))
    records: list[dict] = []
    sub = client.declare_subscriber(audit_key("cellx", "boom"), lambda s: records.append(decode(s.payload)))
    time.sleep(0.3)

    _first_reply(client.get("cellx/boom/cmd", payload=encode({}), timeout=2.0))  # no reply expected
    deadline = time.time() + 5.0
    while time.time() < deadline and not records:
        time.sleep(0.05)
    assert len(records) == 1
    assert records[0]["ok"] is False
    assert "kaput" in records[0]["error"]
    assert records[0]["reply"] is None
    sub.undeclare()
    queryable.undeclare()


def test_audit_truncates_huge_values(linked):
    server, client = linked
    audit = QueryAudit(server, "cellx", "big")

    def handler(query):
        query.reply(str(query.key_expr), encode({"ok": True, "blob": "y" * 10_000}))

    queryable = server.declare_queryable("cellx/big/cmd", audit.wrap(handler))
    records: list[dict] = []
    sub = client.declare_subscriber(audit_key("cellx", "big"), lambda s: records.append(decode(s.payload)))
    time.sleep(0.3)

    _first_reply(client.get("cellx/big/cmd", payload=encode({"blob": "x" * 10_000}), timeout=5.0))
    deadline = time.time() + 5.0
    while time.time() < deadline and not records:
        time.sleep(0.05)
    assert len(records) == 1
    rec = records[0]
    assert "_truncated" in rec["request"] and len(rec["request"]["_truncated"]) <= 2048
    assert "_truncated" in rec["reply"]
    sub.undeclare()
    queryable.undeclare()
