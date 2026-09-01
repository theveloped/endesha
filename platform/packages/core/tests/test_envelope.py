"""Envelope + retained-value helpers over a real zenoh peer link."""

from __future__ import annotations

import threading
import time

import pytest

from wf.core.codec import decode, encode
from wf.core.envelope import (
    CODES,
    EnvelopeError,
    Goal,
    RecentReplies,
    Reply,
    Request,
    WireError,
    call,
    fail,
    new_req_id,
    ok_goal,
    ok_value,
    parse_request,
    request,
)
from wf.core.retained import subscribe_retained
from wf.core.testing import linked_sessions

PREFIX = "cell/envtest"


@pytest.fixture
def linked():
    with linked_sessions() as (server_session, client_session):
        yield server_session, client_session


# ── pure shapes ──────────────────────────────────────────────────────────


def test_wire_error_round_trip_and_closed_codes():
    e = WireError("conflict", "held_by", "program:x", retryable=False)
    assert WireError.from_wire(e.to_wire()) == e
    with pytest.raises(ValueError):
        WireError("nope", "reason")
    # tolerant reader: an unknown code degrades to internal, never raises
    assert WireError.from_wire({"code": "future_code", "reason": "x"}).code == "internal"
    assert all(isinstance(c, str) for c in CODES) and len(CODES) == 8


def test_goal_and_request_round_trip():
    g = Goal("gid", "running", "a/feedback", "a/result", "a/cancel", 60.0)
    assert Goal.from_wire(g.to_wire()) == g
    r = Request.new({"x": 1}, client_id="me")
    assert Request.from_wire(r.to_wire()) == r
    anon = Request.new()
    assert Request.from_wire(anon.to_wire()).client_id is None
    with pytest.raises(ValueError):
        Request.from_wire({"args": {}})  # no req_id: no legacy dialect


def test_reply_branches():
    assert Reply.from_wire(ok_value()) == Reply(ok=True, value={})
    assert Reply.from_wire(ok_value({"a": 1})).value == {"a": 1}
    err = Reply.from_wire(fail("busy", "goal_active", retryable=True))
    assert not err.ok and err.error.code == "busy" and err.error.retryable
    goal = Reply.from_wire(ok_goal(Goal("g", "running", "f", "r", "c")))
    assert goal.ok and goal.goal.goal_id == "g"
    with pytest.raises(ValueError):
        Reply.from_wire({"value": {}})  # missing ok


def test_recent_replies_ring():
    ring = RecentReplies(maxlen=2)
    ring.put("a", {"ok": True})
    ring.put("b", {"ok": False})
    assert ring.get("a") == {"ok": True}
    ring.put("c", {"ok": True})  # evicts "a"
    assert ring.get("a") is None and ring.get("b") is not None


# ── over the bus ─────────────────────────────────────────────────────────


def _serve(session, key, handler):
    q = session.declare_queryable(key, handler)
    time.sleep(0.5)  # let routes propagate over the TCP link
    return q


def test_request_value_and_error_branches(linked):
    server, client = linked
    seen: list[Request] = []

    def handler(query):
        req = parse_request(query)
        seen.append(req)
        if req.args.get("boom"):
            query.reply(str(query.key_expr), encode(fail("conflict", "no_control")))
        else:
            query.reply(str(query.key_expr), encode(ok_value({"echo": req.args["x"]})))

    q = _serve(server, f"{PREFIX}/cmd/echo", handler)
    try:
        reply = request(client, f"{PREFIX}/cmd/echo", {"x": 7}, client_id="me")
        assert reply.ok and reply.value == {"echo": 7}
        assert seen[0].client_id == "me" and seen[0].req_id

        assert call(client, f"{PREFIX}/cmd/echo", {"x": 1}) == {"echo": 1}
        with pytest.raises(EnvelopeError) as exc:
            call(client, f"{PREFIX}/cmd/echo", {"x": 0, "boom": True})
        assert exc.value.code == "conflict" and exc.value.reason == "no_control"
    finally:
        q.undeclare()


def test_absence_is_unavailable(linked):
    _, client = linked
    reply = request(client, f"{PREFIX}/cmd/nobody_home", {}, timeout_s=0.5)
    assert not reply.ok
    assert reply.error.code == "unavailable" and reply.error.reason == "no_reply"
    assert reply.error.retryable


def test_call_follows_goal_to_result(linked):
    server, client = linked
    result_key = f"{PREFIX}/action/g1/result"
    result_wire = ok_value({"final": 42})

    def on_goal(query):
        req = parse_request(query)
        goal = Goal(req.req_id, "running", f"{PREFIX}/action/g1/feedback",
                    result_key, f"{PREFIX}/action/cancel")
        query.reply(str(query.key_expr), encode(ok_goal(goal)))
        # publish the retained result shortly after acceptance
        def later():
            time.sleep(0.3)
            server.put(result_key, encode(result_wire))
        threading.Thread(target=later, daemon=True).start()

    q = _serve(server, f"{PREFIX}/action/run", on_goal)
    rq = _serve(server, result_key, lambda query: query.finalize())  # no result yet on query
    try:
        value = call(client, f"{PREFIX}/action/run", {"speed": 1},
                     client_id="me", result_timeout_s=5.0)
        assert value == {"final": 42}
    finally:
        q.undeclare()
        rq.undeclare()


def test_goal_result_error_raises(linked):
    server, client = linked
    result_key = f"{PREFIX}/action/g2/result"

    def on_goal(query):
        req = parse_request(query)
        goal = Goal(req.req_id, "running", f"{PREFIX}/action/g2/feedback",
                    result_key, f"{PREFIX}/action/cancel")
        query.reply(str(query.key_expr), encode(ok_goal(goal)))

    def on_result_query(query):
        query.reply(result_key, encode(fail("cancelled", "hold")))

    q = _serve(server, f"{PREFIX}/action/run2", on_goal)
    rq = _serve(server, result_key, on_result_query)
    try:
        with pytest.raises(EnvelopeError) as exc:
            call(client, f"{PREFIX}/action/run2", {}, result_timeout_s=5.0)
        assert exc.value.code == "cancelled" and exc.value.reason == "hold"
    finally:
        q.undeclare()
        rq.undeclare()


def test_retained_seed_then_subscribe(linked):
    server, client = linked
    key = f"{PREFIX}/state/thing"
    current = {"t": 1, "v": "seed"}

    def on_query(query):
        query.reply(key, encode(current))

    q = _serve(server, key, on_query)
    got: list[dict] = []
    handle = subscribe_retained(client, key, got.append)
    try:
        assert got and got[0] == {"t": 1, "v": "seed"}
        current = {"t": 2, "v": "delta"}
        server.put(key, encode(current))
        deadline = time.monotonic() + 3.0
        while time.monotonic() < deadline and len(got) < 2:
            time.sleep(0.05)
        assert got[-1] == {"t": 2, "v": "delta"}
    finally:
        handle.close()
        q.undeclare()
