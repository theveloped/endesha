#! /usr/bin/env python
# coding=utf-8

"""
Offline track using Ruckig-generated samples (joint space)

Behavior:
- Define a set of waypoints (supports optional pass-through flags like example_servoj_ruckig)
- Use Ruckig to generate a smooth, near-constant-speed joint trajectory sampled at controller cycle time
- Upload the full sample set into a path buffer in one go and execute it from the controller

Notes:
- Requires the 'ruckig' Python package: pip install ruckig
- Waypoint format supports 6 or 7 elements: [j1..j6] or [j1..j6, smooth]
  where smooth=True requests pass-through at that waypoint; endpoints are treated as stop points.
"""

import time
import math
import pyaubo_sdk

try:
    from ruckig import Ruckig, InputParameter, OutputParameter, Result
    _HAS_RUCKIG = True
except Exception:
    _HAS_RUCKIG = False

M_PI = math.pi


def wait_arrival(impl):
    cnt = 0
    while impl.getMotionControl().getExecId() == -1:
        cnt += 1
        if cnt > 50:
            return -1
        time.sleep(0.05)
    while True:
        if impl.getMotionControl().getExecId() == -1:
            break
        time.sleep(0.05)
    return 0


def wait_pathbuffer_finished(impl):
    while impl.getMotionControl().getExecId() == -1:
        time.sleep(0.05)
    while impl.getMotionControl().getExecId() != -1:
        time.sleep(0.05)


def get_servo_cycle(robot_interface, default_dt=0.005):
    try:
        dt = robot_interface.getRobotConfig().getCycletime()
        if dt and dt > 0:
            return dt
    except Exception:
        pass
    return default_dt


def joints_close(a, b, tol=0.01):
    """Per-joint absolute tolerance (rad); default ~0.57 deg."""
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if abs(x - y) > tol:
            return False
    return True


def generate_ruckig_trajectory(robot_interface, waypoints, dt, vmax=None, amax=None, jmax=None):
    """Generate joint samples at period dt through given waypoints using Ruckig."""
    if not _HAS_RUCKIG:
        raise RuntimeError("ruckig module not available. Install with: pip install ruckig")

    dof = len(waypoints[0])
    cfg = robot_interface.getRobotConfig()

    if vmax is None:
        try:
            vmax_cfg = cfg.getJointMaxSpeeds()
            print("vmax_cfg:", vmax_cfg)
            vmax = [min(1.0, v) * 0.5 for v in vmax_cfg]  # conservative
            print("vmax:", vmax)
        except Exception:
            vmax = [1.0] * dof
    if amax is None:
        try:
            amax_cfg = cfg.getJointMaxAccelerations()
            print("amax_cfg:", amax_cfg)
            amax = [min(2.0, a) * 0.5 for a in amax_cfg]  # conservative
            print("amax:", amax)
        except Exception:
            amax = [1.0] * dof
    if jmax is None:
        jmax = [10.0] * dof  # conservative jerk
        print("jmax:", jmax)

    print("dt:", dt)


    vmax = [10] * dof
    amax = [10.0] * dof
    jmax = [25.0] * dof

    otg = Ruckig(dof, dt)
    ip = InputParameter(dof)
    op = OutputParameter(dof)

    ip.max_velocity = vmax
    ip.max_acceleration = amax
    ip.max_jerk = jmax

    ip.current_position = list(waypoints[0])
    ip.current_velocity = [0.0] * dof
    ip.current_acceleration = [0.0] * dof

    traj = []

    for target in waypoints[1:]:
        ip.target_position = list(target)
        ip.target_velocity = [0.0] * dof
        ip.target_acceleration = [0.0] * dof

        res = otg.update(ip, op)
        if res not in (Result.Working, Result.Finished):
            raise RuntimeError(f"Ruckig update failed with result {res}")

        while res == Result.Working:
            traj.append(list(op.new_position))
            ip.current_position = list(op.new_position)
            ip.current_velocity = list(op.new_velocity)
            ip.current_acceleration = list(op.new_acceleration)
            res = otg.update(ip, op)

        traj.append(list(op.new_position))
        ip.current_position = list(op.new_position)
        ip.current_velocity = [0.0] * dof
        ip.current_acceleration = [0.0] * dof

    return traj


def main():
    robot_ip = "192.168.1.20"
    robot_port = 30004

    rpc = pyaubo_sdk.RpcClient()
    rpc.setRequestTimeout(1000)
    rpc.connect(robot_ip, robot_port)
    if not rpc.hasConnected():
        print("RPC connect failed")
        return -1
    rpc.login("aubo", "123456")
    if not rpc.hasLogined():
        print("Login failed")
        rpc.disconnect()
        return -1

    robot_name = rpc.getRobotNames()[0]
    robot = rpc.getRobotInterface(robot_name)
    mc = robot.getMotionControl()

    # Example waypoints (degrees -> radians), add pass-through flags as needed
    # Waypoints copied from example_movej.py (in radians)
    # Copy/paste into your script:
    q1 = [6.52 * (M_PI / 180), -36.32 * (M_PI / 180), 141.02 * (M_PI / 180), 85.63 * (M_PI / 180), 90.99 * (M_PI / 180), 6.59 * (M_PI / 180)]
    q2 = [1.11 * (M_PI / 180), -26.24 * (M_PI / 180), 126.38 * (M_PI / 180), -28.79 * (M_PI / 180), 93.36 * (M_PI / 180), -0.53 * (M_PI / 180)]
    q3 = [28.85 * (M_PI / 180), -26.24 * (M_PI / 180), 127.17 * (M_PI / 180), -28.79 * (M_PI / 180), 119.32 * (M_PI / 180), -0.53 * (M_PI / 180)]
    q4 = [31.91 * (M_PI / 180), -39.09 * (M_PI / 180), 140.01 * (M_PI / 180), 87.72 * (M_PI / 180), 92.16 * (M_PI / 180), 32.84 * (M_PI / 180)]
    q5 = [37.76 * (M_PI / 180), -11.68 * (M_PI / 180), 128.6 * (M_PI / 180), -48.7 * (M_PI / 180), 38.24 * (M_PI / 180), 6.39 * (M_PI / 180)]
    q6 = [51.78 * (M_PI / 180), -8.72 * (M_PI / 180), 100.22 * (M_PI / 180), 19.18 * (M_PI / 180), 94.34 * (M_PI / 180), 47.3 * (M_PI / 180)]
    q7 = [53.76 * (M_PI / 180), -0.17 * (M_PI / 180), 7.22 * (M_PI / 180), 8.31 * (M_PI / 180), 33.63 * (M_PI / 180), 82.81 * (M_PI / 180)]
    q8 = [-88.43 * (M_PI / 180), -1.79 * (M_PI / 180), 152.58 * (M_PI / 180), 75.01 * (M_PI / 180), -1.44 * (M_PI / 180), 82.81 * (M_PI / 180)]
    q9 = [-6.93 * (M_PI / 180), -12.09 * (M_PI / 180), 127.39 * (M_PI / 180), -38.23 * (M_PI / 180), 83.28 * (M_PI / 180), 82.82 * (M_PI / 180)]
    waypoints = [q1, q2, q3, q4, q5, q6, q7, q8, q9, q1]

    # Move to the first sample to avoid overshoot
    dt = get_servo_cycle(robot)
    print(f"Controller cycle dt={dt:.4f}s")

    # Generate samples
    traj = generate_ruckig_trajectory(robot, waypoints, dt)

    # Move to first point (skip if already at first sample within tolerance)
    first_q = traj[0]
    mc.setSpeedFraction(0.5)
    current_q = robot.getRobotState().getJointPositions()
    if joints_close(current_q, first_q):
        print("Already at initial point; skipping pre-position move")
    else:
        mc.moveJoint(first_q, 80/180*M_PI, 60/180*M_PI, 0.0, 0.0)
        if wait_arrival(robot) != 0:
            # If motion didn't start, but we ended up close to the target, accept it
            current_q = robot.getRobotState().getJointPositions()
            if not joints_close(current_q, first_q):
                print("Failed to reach initial point")
                rpc.disconnect()
                return -1

    # Upload samples to path buffer and execute
    name = "rec"
    try:
        mc.pathBufferFree(name)
    except Exception:
        pass
    mc.pathBufferAlloc(name, 2, len(traj))  # 2 == joint trajectory

    # Append in chunks
    chunk = 50
    for i in range(0, len(traj), chunk):
        mc.pathBufferAppend(name, traj[i:i+chunk])

    # Build per-joint limits for evaluation (must match DOF)
    dof = len(traj[0])
    try:
        vmax_cfg = robot.getRobotConfig().getJointMaxSpeeds()
        amax_cfg = robot.getRobotConfig().getJointMaxAccelerations()
        # Be conservative: use a fraction of the reported limits
        v_eval = [min(0.5, vmax_cfg[j]) for j in range(dof)]
        a_eval = [min(1.0, amax_cfg[j]) for j in range(dof)]
        print("vmax_cfg:", vmax_cfg)
        print("v_eval:", v_eval)
        print("amax_cfg:", amax_cfg)
        print("a_eval:", a_eval)
    except Exception:
        v_eval = [1.0] * dof
        a_eval = [1.0] * dof

    interval = dt  # for type=2 buffers, t is the sampling interval
    print("dt:", interval)
    print("pathBufferEval:", mc.pathBufferEval(name, a_eval, v_eval, interval))
    while not mc.pathBufferValid(name):
        time.sleep(0.01)

    mc.movePathBuffer(name)
    wait_pathbuffer_finished(robot)
    print("PathBuffer execution finished")

    rpc.disconnect()
    return 0


if __name__ == '__main__':
    main()
