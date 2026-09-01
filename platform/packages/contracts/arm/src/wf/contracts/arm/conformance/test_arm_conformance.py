"""Conformance tests 1-9: arm contract, hardware-facing; bus-only.

Tests 7-9 (frames v0) need no config service: ``set_tcp`` accepts the
reserved ``flange`` name without a store lookup, and a base-frame pose
target resolves as identity on an empty frame tree.
"""

from __future__ import annotations

import contextlib
import math
import os
import time
import uuid

import pytest

from wf.contracts.arm import keys
from wf.contracts.arm.messages import (
    Ack,
    ArmStatus,
    ExecutePathGoal,
    FlangeState,
    IoState,
    JogCommand,
    JointState,
    SetDo,
    Waypoint,
)
from wf.contracts.control import keys as control_keys
from wf.contracts.control.messages import ControlOwnerState
from wf.core.envelope import Reply, request as envelope_request
from wf.core.action import ActionClient, ActionRejected
from wf.core.codec import decode, encode

from .conftest import collect_samples, first_sample


def _query_ack(session, key: str, payload: dict, timeout_s: float = 5.0) -> Ack:
    replies = session.get(key, payload=encode(payload), timeout=timeout_s)
    for reply in replies:
        if reply.ok is not None:
            return Ack.from_wire(decode(reply.ok.payload))
    pytest.fail(f"no reply from {key}")


def _latest_q(session, realm: str, rid: str) -> list[float]:
    joints = JointState.from_wire(
        first_sample(session, keys.state_joints(realm, rid), timeout_s=2.0)
    )
    return joints.q


def _acquire(session, realm, rid, client_id, user="conf") -> Reply:
    # The lease is cell-level (``wf.contracts.control``); ``rid`` is unused but
    # kept so the helpers read like the rest of the suite.
    reply = envelope_request(session, control_keys.cmd_acquire(realm),
                             {"user": user}, client_id=client_id, timeout_s=5.0)
    if not reply.ok and reply.error.reason == "no_reply":
        pytest.fail("no reply from control/cmd/acquire")
    return reply


def _release(session, realm, rid, client_id) -> None:
    envelope_request(session, control_keys.cmd_release(realm), {},
                     client_id=client_id, timeout_s=5.0)


@contextlib.contextmanager
def _lease(session, realm, rid, user="conf"):
    cid = str(uuid.uuid4())
    ack = _acquire(session, realm, rid, cid, user)
    assert ack.ok, ack.error
    try:
        yield cid
    finally:
        _release(session, realm, rid, cid)


def _wait_owner(session, realm, rid, predicate, timeout_s: float = 3.0):
    """Poll latest-wins ``control/state/owner`` until ``predicate(state)``."""
    deadline = time.monotonic() + timeout_s
    last = None
    while time.monotonic() < deadline:
        samples = collect_samples(
            session, control_keys.state_owner(realm),
            duration_s=0.6, min_count=1,
        )
        for raw in samples:
            last = ControlOwnerState.from_wire(raw)
            if predicate(last):
                return last
    return last


def test_joints_stream(session, realm, rid):
    samples = collect_samples(
        session, keys.state_joints(realm, rid), duration_s=2.0, min_count=10**9
    )
    assert len(samples) >= 20, f"only {len(samples)} joint samples in 2s"
    ts = []
    for raw in samples:
        joints = JointState.from_wire(raw)
        assert len(joints.q) == 6
        ts.append(joints.t)
    assert all(b > a for a, b in zip(ts, ts[1:])), "t not strictly increasing"


def test_flange_stream(session, realm, rid):
    flange = FlangeState.from_wire(
        first_sample(session, keys.state_flange(realm, rid), timeout_s=2.0)
    )
    assert flange.pose.frame == f"arm/{rid}/base"
    norm = math.sqrt(sum(v * v for v in flange.pose.quat))
    assert abs(norm - 1.0) < 1e-6


def test_status_keepalive(session, realm, rid):
    status = ArmStatus.from_wire(
        first_sample(session, keys.state_status(realm, rid), timeout_s=2.0)
    )
    assert status.state_rate_hz > 50


def test_set_do_roundtrip(session, realm, rid):
    pin_env = os.environ.get("WF_CONF_TEST_DO_PIN")
    if pin_env is None:
        pytest.skip("WF_CONF_TEST_DO_PIN not set")
    pin = int(pin_env)

    io = IoState.from_wire(
        first_sample(session, keys.state_io(realm, rid), timeout_s=2.0)
    )
    original = bool(io.do_ >> pin & 1)
    target = not original

    try:
        ack = _query_ack(
            session,
            keys.cmd_set_do(realm, rid),
            SetDo(bank="standard", pin=pin, value=target).to_wire(),
        )
        assert ack.ok, ack.error

        deadline = time.monotonic() + 1.0
        flipped = False
        while time.monotonic() < deadline:
            io = IoState.from_wire(
                first_sample(session, keys.state_io(realm, rid), timeout_s=1.0)
            )
            if bool(io.do_ >> pin & 1) == target:
                flipped = True
                break
        assert flipped, f"do bit {pin} did not flip to {target} within 1s"
    finally:
        ack = _query_ack(
            session,
            keys.cmd_set_do(realm, rid),
            SetDo(bank="standard", pin=pin, value=original).to_wire(),
        )
        assert ack.ok, ack.error


def test_execute_path_lifecycle_zero_motion(session, realm, rid):
    q = _latest_q(session, realm, rid)
    client = ActionClient(session, keys.action_prefix(realm, rid), "execute_path")
    with _lease(session, realm, rid) as cid:
        goal_msg = ExecutePathGoal(
            waypoints=[Waypoint(type="movej", target={"q": q})], client_id=cid
        )

        goal = client.send(goal_msg.to_wire())
        result = goal.result(timeout_s=30.0)
        assert result["state"] == "succeeded", result
        assert result["ok"] is True

        # Result re-query returns the cached result.
        replies = session.get(
            f"{keys.action_prefix(realm, rid)}/{goal.goal_id}/result", timeout=5.0
        )
        cached = None
        for reply in replies:
            if reply.ok is not None:
                cached = decode(reply.ok.payload)
                break
        assert cached is not None, "result queryable did not reply"
        assert cached["state"] == "succeeded"
        assert cached["t"] == result["t"]

        # Idempotent resubmission: accepted with terminal state, no re-execution.
        goal2 = client.send(goal_msg.to_wire(), goal_id=goal.goal_id)
        result2 = goal2.result(timeout_s=5.0)
        assert result2["state"] == "succeeded"
        assert result2["t"] == result["t"], "goal was re-executed"


def test_cancel_and_busy(session, realm, rid):
    if os.environ.get("WF_CONF_ALLOW_MOTION") != "1":
        pytest.skip("WF_CONF_ALLOW_MOTION != 1")

    q = _latest_q(session, realm, rid)
    q_moved = list(q)
    q_moved[5] += math.radians(5.0)

    client = ActionClient(session, keys.action_prefix(realm, rid), "execute_path")
    with _lease(session, realm, rid) as cid:
        goal = client.send(
            ExecutePathGoal(
                waypoints=[
                    Waypoint(type="movej", target={"q": q_moved}),
                    Waypoint(type="movej", target={"q": q}),
                ],
                client_id=cid,
            ).to_wire()
        )

        # Second goal while the first runs must be rejected busy (busy is
        # checked before the lease gate, so client_id is irrelevant here).
        time.sleep(0.3)
        with pytest.raises(ActionRejected) as excinfo:
            client.send(
                ExecutePathGoal(
                    waypoints=[Waypoint(type="movej", target={"q": q})],
                    client_id=cid,
                ).to_wire()
            )
        assert excinfo.value.reason == "busy"

        # Cancel the first: terminal canceled within 5 s.
        cancel_reply = goal.cancel()
        assert cancel_reply["state"] in ("canceling", "canceled")
        result = goal.result(timeout_s=5.0)
        assert result["state"] == "canceled", result


def test_set_tcp_roundtrip(session, realm, rid):
    ack = _query_ack(session, keys.cmd_set_tcp(realm, rid), {"name": "flange"})
    assert ack.ok, ack.error

    ack = _query_ack(
        session, keys.cmd_set_tcp(realm, rid), {"name": "conformance_missing_tcp"}
    )
    assert not ack.ok
    assert ack.error.startswith("tcp_unknown:"), ack.error

    status = ArmStatus.from_wire(
        first_sample(session, keys.state_status(realm, rid), timeout_s=2.0)
    )
    assert status.active_tcp == "flange"


def test_pose_target_unknown_frame(session, realm, rid):
    client = ActionClient(session, keys.action_prefix(realm, rid), "execute_path")
    with _lease(session, realm, rid) as cid:
        goal = ExecutePathGoal(
            waypoints=[
                Waypoint(
                    type="movej",
                    target={
                        "pose": {
                            "frame": "conformance/no_such_frame",
                            "xyz": [0.0, 0.0, 0.0],
                            "quat": [0.0, 0.0, 0.0, 1.0],
                        }
                    },
                )
            ],
            client_id=cid,
        )
        with pytest.raises(ActionRejected) as excinfo:
            client.send(goal.to_wire())
    assert excinfo.value.reason.startswith("frame_unknown:"), excinfo.value.reason


def test_execute_path_pose_target(session, realm, rid):
    if os.environ.get("WF_CONF_ALLOW_MOTION") != "1":
        pytest.skip("WF_CONF_ALLOW_MOTION != 1")

    flange = FlangeState.from_wire(
        first_sample(session, keys.state_flange(realm, rid), timeout_s=2.0)
    )
    # frame = arm/{rid}/base -> identity resolve on an empty tree; the IK
    # lands at (approximately) the current q -> near-zero motion.
    client = ActionClient(session, keys.action_prefix(realm, rid), "execute_path")
    with _lease(session, realm, rid) as cid:
        goal = ExecutePathGoal(
            waypoints=[
                Waypoint(type="movej", target={"pose": flange.pose.to_wire()})
            ],
            client_id=cid,
        )
        result = client.send(goal.to_wire()).result(timeout_s=30.0)
    assert result["state"] == "succeeded", result

    snapshot = result["data"]["snapshot"]
    resolved_q = snapshot["waypoints"][0]["resolved_q"]
    assert isinstance(resolved_q, list) and len(resolved_q) == 6
    assert all(isinstance(v, float) for v in resolved_q)
    assert snapshot["active_tcp"] == "flange"


def test_control_lease(session, realm, rid):
    cid_a = str(uuid.uuid4())
    cid_b = str(uuid.uuid4())
    ack_a = _acquire(session, realm, rid, cid_a, user="alice")
    assert ack_a.ok, ack_a.error
    owner_a = ControlOwnerState.from_wire(ack_a.value).owner
    assert owner_a is not None and owner_a.user == "alice"
    try:
        state = _wait_owner(
            session, realm, rid,
            lambda s: s.owner is not None and s.owner.client_id == cid_a,
        )
        assert state is not None and state.owner is not None
        assert state.owner.client_id == cid_a

        # A different client is refused while A holds the lease.
        ack_b = _acquire(session, realm, rid, cid_b, user="bob")
        assert ack_b.ok is False
        assert ack_b.error.reason == "held_by", ack_b.error
    finally:
        _release(session, realm, rid, cid_a)

    freed = _wait_owner(session, realm, rid, lambda s: s.owner is None)
    assert freed is not None and freed.owner is None, "owner not freed after release"


def test_execute_path_requires_lease(session, realm, rid):
    q = _latest_q(session, realm, rid)
    client = ActionClient(session, keys.action_prefix(realm, rid), "execute_path")

    # No client_id -> rejected before any precondition.
    goal = ExecutePathGoal(waypoints=[Waypoint(type="movej", target={"q": q})])
    with pytest.raises(ActionRejected) as excinfo:
        client.send(goal.to_wire())
    assert excinfo.value.reason == "no_control", excinfo.value.reason

    # With a held lease + client_id the same (zero-motion) goal succeeds.
    with _lease(session, realm, rid) as cid:
        goal2 = ExecutePathGoal(
            waypoints=[Waypoint(type="movej", target={"q": q})], client_id=cid
        )
        result = client.send(goal2.to_wire()).result(timeout_s=30.0)
    assert result["state"] == "succeeded", result


def test_jog_moves_and_watchdog(session, realm, rid):
    if os.environ.get("WF_CONF_ALLOW_MOTION") != "1":
        pytest.skip("WF_CONF_ALLOW_MOTION != 1")

    with _lease(session, realm, rid) as cid:
        q0 = _latest_q(session, realm, rid)
        pub = session.declare_publisher(keys.cmd_jog(realm, rid))
        try:
            deadline = time.monotonic() + 0.5
            while time.monotonic() < deadline:
                pub.put(
                    encode(
                        JogCommand(
                            client_id=cid, mode="joint", frame="base",
                            velocity=[0.1, 0.0, 0.0, 0.0, 0.0, 0.0],
                            t=time.time_ns(),
                        ).to_wire()
                    )
                )
                time.sleep(1.0 / 15.0)
            q1 = _latest_q(session, realm, rid)
            assert abs(q1[0] - q0[0]) > 1e-3, "jog did not move joint 0"
        finally:
            pub.undeclare()

        # Watchdog: stop publishing; after the 250 ms watchdog the arm holds.
        time.sleep(0.4)
        qa = _latest_q(session, realm, rid)
        time.sleep(0.2)
        qb = _latest_q(session, realm, rid)
        assert all(abs(a - b) < 1e-3 for a, b in zip(qa, qb)), "watchdog did not halt jog"
