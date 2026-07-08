"""Wire roundtrip tests for every arm contract message."""

import pytest

import math

from wf.contracts.arm.messages import (
    Ack,
    AcquireControl,
    ArmStatus,
    ControlAck,
    ControlOwner,
    ControlOwnerState,
    ExecutePathGoal,
    FlangeState,
    Freedom,
    IoState,
    JogCommand,
    JointState,
    Pose,
    SetDo,
    TcpState,
    Waypoint,
)

OWNER = ControlOwner(client_id="c1", user="me", granted_at=10, expires_at=40)

POSE = Pose(frame="arm/r1/base", xyz=[0.1, -0.2, 0.3], quat=[0.0, 0.0, 0.0, 1.0])


@pytest.mark.parametrize(
    "msg",
    [
        POSE,
        JointState(t=1, q=[0.0] * 6, qd=[0.1] * 6, tau=[0.5] * 6, clock_domain="robot_controller"),
        FlangeState(t=2, pose=POSE),
        TcpState(t=3, tcp_name="flange", pose=POSE),
        IoState(t=4, di=0b1010, do_=0b0101, ai=[0.1, 0.2], ao=[0.3, 0.4]),
        ArmStatus(
            t=5,
            mode="running",
            servo_on=True,
            estop=False,
            protective_stop=False,
            speed_scale=0.5,
            active_tcp="flange",
            error=None,
            state_rate_hz=200.0,
        ),
        SetDo(bank="standard", pin=1, value=True),
        Ack(ok=False, error="nope"),
        Waypoint(type="movej", target={"q": [0.0] * 6}, speed=1.0, blend_radius=0.01),
        ExecutePathGoal(waypoints=[Waypoint(type="movej", target={"q": [1.0] * 6})]),
        ExecutePathGoal(
            waypoints=[Waypoint(type="movej", target={"q": [1.0] * 6})],
            client_id="lease-1",
        ),
        Freedom(dof="yaw"),
        Freedom(dof="pitch", frame="tool", min=-1.0, max=1.0, step=0.1),
        Freedom(dof="z", min=-0.05, max=0.05, step=0.01),
        JogCommand(
            client_id="c1", mode="cartesian", frame="base",
            velocity=[0.05, 0.0, 0.0, 0.0, 0.0, 0.0], t=99,
        ),
        JogCommand(
            client_id="c1", mode="joint", frame="base",
            velocity=[0.1, 0.0, 0.0, 0.0, 0.0, 0.0], t=100,
        ),
        OWNER,
        AcquireControl(client_id="c1", user="me"),
        ControlAck(ok=True, owner=OWNER, error=None),
        ControlAck(ok=False, owner=None, error="held_by:bob"),
        ControlOwnerState(t=7, owner=OWNER),
        ControlOwnerState(t=8, owner=None),
    ],
    ids=lambda m: type(m).__name__,
)
def test_wire_roundtrip(msg):
    assert type(msg).from_wire(msg.to_wire()) == msg


def test_iostate_wire_key_is_do():
    wire = IoState(t=1, di=0, do_=0b11, ai=[], ao=[]).to_wire()
    assert "do" in wire and "do_" not in wire
    assert wire["do"] == 3
    assert IoState.from_wire(wire).do_ == 3


def test_pose_rejects_bad_quat_length():
    with pytest.raises(ValueError):
        Pose(frame="f", xyz=[0, 0, 0], quat=[0, 0, 1])


def test_pose_rejects_bad_xyz_length():
    with pytest.raises(ValueError):
        Pose(frame="f", xyz=[0, 0], quat=[0, 0, 0, 1])


def test_setdo_rejects_unknown_bank():
    with pytest.raises(ValueError):
        SetDo(bank="aux", pin=0, value=True)


def test_freedom_free_rotation_defaults_full_circle():
    f = Freedom(dof="yaw")
    assert f.is_rotation and f.axis == 2
    assert f.min == pytest.approx(-math.pi)
    assert f.max == pytest.approx(math.pi)
    assert f.step == pytest.approx(math.radians(5.0))


def test_freedom_translation_requires_bounds():
    with pytest.raises(ValueError):
        Freedom(dof="z")  # no min/max
    with pytest.raises(ValueError):
        Freedom(dof="z", min=-0.1, max=0.1)  # no step


def test_freedom_rejects_partial_rotation_bounds():
    with pytest.raises(ValueError):
        Freedom(dof="roll", min=-1.0)  # only one bound


def test_freedom_rejects_bad_dof_and_frame():
    with pytest.raises(ValueError):
        Freedom(dof="nope")
    with pytest.raises(ValueError):
        Freedom(dof="yaw", frame="world")


def test_freedom_rejects_bad_range_and_step():
    with pytest.raises(ValueError):
        Freedom(dof="yaw", min=1.0, max=-1.0, step=0.1)
    with pytest.raises(ValueError):
        Freedom(dof="yaw", min=-1.0, max=1.0, step=0.0)
