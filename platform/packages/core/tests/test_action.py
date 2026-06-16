"""Appendix-A lifecycle suite over a real zenoh peer link (no router)."""

from __future__ import annotations

import time

import pytest

from wf.core.action import (
    UNKNOWN_GOAL,
    ActionClient,
    ActionRejected,
    ActionServer,
    GoalHandle,
)
from wf.core.codec import decode, encode
from wf.core.testing import linked_sessions

PREFIX = "live/arm/test/action"


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
        "toy", on_accept or (lambda goal: None), on_execute or toy_execute()
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
        result = goal.result(timeout_s=10.0)
        assert result["state"] == "succeeded"
        assert result["ok"] is True
        assert result["error"] is None
        assert result["data"] == {"echo": 42}
        deadline = time.monotonic() + 2.0
        while not feedback and time.monotonic() < deadline:
            time.sleep(0.05)
        assert len(feedback) >= 1
        assert feedback[0]["goal_id"] == goal.goal_id
        assert feedback[0]["state"] == "running"
        assert 0.0 < feedback[0]["progress"] <= 1.0
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
        assert result["state"] == "canceled"
        assert result["ok"] is False
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
        assert excinfo.value.reason == "busy"
        assert goal.result(timeout_s=10.0)["state"] == "succeeded"
    finally:
        server.close()


def test_idempotent_resubmit(linked):
    server_session, client_session = linked
    server = make_server(server_session)
    try:
        client = ActionClient(client_session, PREFIX, "toy")
        goal = client.send({"x": 1})
        result1 = goal.result(timeout_s=10.0)
        assert result1["state"] == "succeeded"

        goal2 = client.send({"x": 1}, goal_id=goal.goal_id)
        result2 = goal2.result(timeout_s=5.0)
        assert result2["t"] == result1["t"], "goal was re-executed"
    finally:
        server.close()


def test_result_ttl_expiry(linked):
    server_session, client_session = linked
    server = make_server(server_session, result_ttl_s=0.5)
    try:
        client = ActionClient(client_session, PREFIX, "toy")
        goal = client.send({})
        assert goal.result(timeout_s=10.0)["state"] == "succeeded"

        time.sleep(0.8)
        # Trigger lazy pruning + query the expired result.
        replies = client_session.get(
            f"{PREFIX}/{goal.goal_id}/result", timeout=5.0
        )
        payloads = [decode(r.ok.payload) for r in replies if r.ok is not None]
        assert len(payloads) == 1
        assert payloads[0]["state"] == UNKNOWN_GOAL
        assert payloads[0]["ok"] is False
        assert payloads[0]["error"] == UNKNOWN_GOAL
    finally:
        server.close()


def test_cancel_unknown_goal(linked):
    server_session, client_session = linked
    server = make_server(server_session)
    try:
        replies = client_session.get(
            f"{PREFIX}/cancel",
            payload=encode({"goal_id": "no-such-goal"}),
            timeout=5.0,
        )
        payloads = [decode(r.ok.payload) for r in replies if r.ok is not None]
        assert len(payloads) == 1
        assert payloads[0]["state"] == UNKNOWN_GOAL
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
        assert result["state"] == "failed"
        assert result["ok"] is False
        assert "boom" in result["error"]
    finally:
        server.close()


def test_on_accept_rejection_reason(linked):
    server_session, client_session = linked
    server = make_server(server_session, on_accept=lambda goal: "target_outside_limits")
    try:
        client = ActionClient(client_session, PREFIX, "toy")
        with pytest.raises(ActionRejected) as excinfo:
            client.send({})
        assert excinfo.value.reason == "target_outside_limits"
    finally:
        server.close()
