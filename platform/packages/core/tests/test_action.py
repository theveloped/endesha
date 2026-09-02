"""Appendix-A lifecycle suite over a real zenoh peer link (no router) —
envelope protocol (wire-contract RFC §4.2–§4.3)."""

from __future__ import annotations

import time

import pytest

from wf.core.action import (
    UNKNOWN_GOAL,
    ActionClient,
    ActionFailed,
    ActionRejected,
    ActionServer,
    GoalHandle,
)
from wf.core.codec import decode, encode
from wf.core.envelope import Request
from wf.core.testing import linked_sessions

PREFIX = "cell/arm/test/action"


def toy_execute(duration_s: float = 0.3):
    """An executor that sleeps in 50 ms ticks, emits feedback, honors cancel."""

    def on_execute(handle: GoalHandle) -> None:
        ticks = max(1, int(duration_s / 0.05))
        for i in range(ticks):
            if handle.cancel_requested:
                handle.set_canceled()
                return
            handle.feedback(progress=(i + 1) / ticks, tick=i)
            time.sleep(0.05)
        handle.succeed(echo=handle.goal.get("x"))

    return on_execute


@pytest.fixture
def linked():
    with linked_sessions() as (server_session, client_session):
        yield server_session, client_session


def make_server(session, on_accept=None, on_execute=None, **kwargs) -> ActionServer:
    server = ActionServer(session, PREFIX, **kwargs)
    server.register(
        "toy", on_accept or (lambda goal, client_id: None), on_execute or toy_execute()
    )
    # Let queryable/subscriber routes propagate over the TCP link.
    time.sleep(0.5)
    return server


def test_lifecycle_succeeded_with_feedback(linked):
    server_session, client_session = linked
    server = make_server(server_session)
    try:
        feedback: list[dict] = []
        client = ActionClient(client_session, PREFIX, "toy")
        goal = client.send({"x": 42}, on_feedback=feedback.append)
        # the accept reply carries the self-describing follow keys
        assert goal.info is not None
        assert goal.info.goal_id == goal.goal_id
        assert goal.info.result_key.endswith(f"{goal.goal_id}/result")
        assert goal.info.cancel_key.endswith("/cancel")
        result = goal.result(timeout_s=10.0)
        assert result.ok and result.value == {"echo": 42}
        assert goal.value(timeout_s=1.0) == {"echo": 42}
        deadline = time.monotonic() + 2.0
        while not feedback and time.monotonic() < deadline:
            time.sleep(0.05)
        assert len(feedback) >= 1
        fb = feedback[0]
        assert fb["goal_id"] == goal.goal_id
        assert fb["state"] == "running"
        assert 0.0 < fb["progress"] <= 1.0
        assert fb["seq"] >= 1
        assert fb["detail"] == {"tick": 0}
    finally:
        server.close()


def test_cancel_mid_run(linked):
    server_session, client_session = linked
    server = make_server(server_session, on_execute=toy_execute(duration_s=5.0))
    try:
        client = ActionClient(client_session, PREFIX, "toy")
        goal = client.send({})
        time.sleep(0.2)
        reply = goal.cancel()
        assert reply["state"] in ("canceling", "canceled")
        result = goal.result(timeout_s=5.0)
        assert not result.ok
        assert result.error.code == "cancelled" and result.error.reason == "canceled"
        with pytest.raises(ActionFailed) as excinfo:
            goal.value(timeout_s=1.0)
        assert excinfo.value.error.code == "cancelled"
    finally:
        server.close()


def test_busy_rejection(linked):
    server_session, client_session = linked
    server = make_server(server_session, on_execute=toy_execute(duration_s=2.0))
    try:
        client = ActionClient(client_session, PREFIX, "toy")
        goal = client.send({})
        time.sleep(0.1)
        with pytest.raises(ActionRejected) as excinfo:
            client.send({})
        assert excinfo.value.error.code == "busy"
        assert excinfo.value.error.reason == "goal_active"
        assert excinfo.value.error.detail == goal.goal_id
        assert excinfo.value.error.retryable
        assert goal.result(timeout_s=10.0).ok
    finally:
        server.close()


def test_idempotent_resubmit(linked):
    server_session, client_session = linked
    executions: list[str] = []

    def counting_execute(handle: GoalHandle) -> None:
        executions.append(handle.goal_id)
        handle.succeed(echo=handle.goal.get("x"))

    server = make_server(server_session, on_execute=counting_execute)
    try:
        client = ActionClient(client_session, PREFIX, "toy")
        goal = client.send({"x": 1})
        assert goal.result(timeout_s=10.0).ok

        goal2 = client.send({"x": 1}, goal_id=goal.goal_id)
        assert goal2.result(timeout_s=5.0).ok
        assert executions == [goal.goal_id], "goal was re-executed"
    finally:
        server.close()


def test_result_ttl_expiry(linked):
    server_session, client_session = linked
    server = make_server(server_session, result_ttl_s=0.5)
    try:
        client = ActionClient(client_session, PREFIX, "toy")
        goal = client.send({})
        assert goal.result(timeout_s=10.0).ok

        time.sleep(0.8)
        # Trigger lazy pruning + query the expired result.
        replies = client_session.get(
            f"{PREFIX}/{goal.goal_id}/result", timeout=5.0
        )
        payloads = [decode(r.ok.payload) for r in replies if r.ok is not None]
        assert len(payloads) == 1
        assert payloads[0]["ok"] is False
        assert payloads[0]["error"]["code"] == "not_found"
        assert payloads[0]["error"]["reason"] == UNKNOWN_GOAL
    finally:
        server.close()


def test_cancel_unknown_goal(linked):
    server_session, client_session = linked
    server = make_server(server_session)
    try:
        replies = client_session.get(
            f"{PREFIX}/cancel",
            payload=encode(Request.new({"goal_id": "no-such-goal"}).to_wire()),
            timeout=5.0,
        )
        payloads = [decode(r.ok.payload) for r in replies if r.ok is not None]
        assert len(payloads) == 1
        assert payloads[0]["ok"] is False
        assert payloads[0]["error"]["reason"] == UNKNOWN_GOAL
    finally:
        server.close()


def test_legacy_request_rejected(linked):
    """No legacy dialect: a goal submit without req_id is invalid."""
    server_session, client_session = linked
    server = make_server(server_session)
    try:
        replies = client_session.get(
            f"{PREFIX}/toy",
            payload=encode({"goal_id": "old-style", "goal": {}}),
            timeout=5.0,
        )
        payloads = [decode(r.ok.payload) for r in replies if r.ok is not None]
        assert len(payloads) == 1
        assert payloads[0]["ok"] is False
        assert payloads[0]["error"]["code"] == "invalid"
    finally:
        server.close()


def test_on_execute_raises_becomes_failed(linked):
    server_session, client_session = linked

    def explode(handle: GoalHandle) -> None:
        raise RuntimeError("boom")

    server = make_server(server_session, on_execute=explode)
    try:
        client = ActionClient(client_session, PREFIX, "toy")
        goal = client.send({})
        result = goal.result(timeout_s=10.0)
        assert not result.ok
        assert result.error.code == "internal" and result.error.reason == "failed"
        assert "boom" in result.error.detail
    finally:
        server.close()


def test_on_accept_rejection_reason(linked):
    server_session, client_session = linked
    server = make_server(
        server_session, on_accept=lambda goal, client_id: "target_outside_limits"
    )
    try:
        client = ActionClient(client_session, PREFIX, "toy")
        with pytest.raises(ActionRejected) as excinfo:
            client.send({})
        assert excinfo.value.reason == "target_outside_limits"
        assert excinfo.value.error.code == "invalid"
    finally:
        server.close()


def test_client_id_reaches_accept(linked):
    server_session, client_session = linked
    seen: list[str | None] = []

    def accept(goal, client_id):
        seen.append(client_id)
        return None

    server = make_server(server_session, on_accept=accept)
    try:
        client = ActionClient(client_session, PREFIX, "toy")
        goal = client.send({"x": 1}, client_id="op:1")
        assert goal.result(timeout_s=10.0).ok
        assert seen == ["op:1"]
    finally:
        server.close()
