"""Diagnostic: which SDK call physically stops path-buffer motion?

Standalone — talks pyaubo_sdk directly (no wf driver involvement) so the
stop candidate is issued from the SAME RPC session that owns the motion.
Runs ONE candidate per invocation (the robot sweeps j1 between -77 and +40
deg, alternating start/target automatically based on the current pose).

Usage (workspace venv = vendored pyaubo 0.26.0rc6):
    uv run python scripts/probe_stop.py <candidate>
Against the PyPI 0.24.1 binding (matches controller SERVER 0.24):
    uv run --no-project --with pyaubo-sdk==0.24.1 python scripts/probe_stop.py <candidate>

Candidates:
    none          control run: no stop, motion must complete
    stop_move     mc.stopMove(True, True)            [0.26 shim path]
    move_stop     mc.moveStop()                      [if binding has it]
    stop_joint    mc.stopJoint(3.0)
    stop_line     mc.stopLine(3.0, 3.0)
    servo_mode    mc.setServoMode(True); sleep 0.2; setServoMode(False)
    move_preempt  mc.moveJoint(current_q, ...) mid-motion
    path_free     mc.pathBufferFree(buffer)

Reports: rc, time-to-standstill, final vs target j1, STOPPED EARLY verdict,
safety mode after (auto-unlocks a tripped protective stop on exit).
"""

import math
import sys
import time

import pyaubo_sdk

IP = "192.168.188.20"
PORT = 30004
USER, PASS = "aubo", "123456"
BUF = "probe_traj"
DT = 0.005
VMAX = [1.5] * 6
AMAX = [3.0] * 6
SWEEP_LOW_DEG = -77.0
SWEEP_HIGH_DEG = 40.0
STOP_AFTER_S = 0.4  # how far into the motion the candidate fires
STILL_EPS_RAD = 1e-5  # max joint delta per 50 ms poll to count as standstill


def connect():
    rpc = pyaubo_sdk.RpcClient()
    rpc.setRequestTimeout(5000)
    rpc.connect(IP, PORT)
    if not rpc.hasConnected():
        raise ConnectionError(f"cannot connect {IP}:{PORT}")
    rpc.login(USER, PASS)
    if not rpc.hasLogined():
        raise ConnectionError("login failed")
    robot = rpc.getRobotInterface(rpc.getRobotNames()[0])
    return rpc, robot


def unlock_if_protective(state, rm) -> None:
    if "Protective" in str(state.getSafetyModeType()):
        print("clearing protective stop...")
        rm.setUnlockProtectiveStop()
        time.sleep(1.5)
        print("safety:", state.getSafetyModeType())


def apply_candidate(name, mc, q_now):
    if name == "none":
        return "n/a"
    if name == "stop_move":
        return mc.stopMove(True, True)
    if name == "move_stop":
        return mc.moveStop()
    if name == "stop_joint":
        return mc.stopJoint(3.0)
    if name == "stop_line":
        return mc.stopLine(3.0, 3.0)
    if name == "servo_mode":
        rc = mc.setServoMode(True)
        time.sleep(0.2)
        rc2 = mc.setServoMode(False)
        return f"on={rc} off={rc2}"
    if name == "move_preempt":
        return mc.moveJoint(q_now, 80 * math.pi / 180, 60 * math.pi / 180, 0.0, 0.0)
    if name == "path_free":
        return mc.pathBufferFree(BUF)
    raise SystemExit(f"unknown candidate {name!r}")


def main() -> None:
    candidate = sys.argv[1] if len(sys.argv) > 1 else "none"
    rpc, robot = connect()
    state = robot.getRobotState()
    mc = robot.getMotionControl()
    rm = robot.getRobotManage()

    print("pyaubo:", getattr(pyaubo_sdk, "__version__", "unknown"))
    surface = ("moveStop", "stopMove", "stopJoint", "stopLine", "setServoMode")
    print("binding surface:", {m: hasattr(mc, m) for m in surface})

    unlock_if_protective(state, rm)
    sf = mc.getSpeedFraction()

    q0 = list(state.getJointPositions())
    j1_deg = math.degrees(q0[0])
    target_deg = SWEEP_HIGH_DEG if j1_deg < (SWEEP_LOW_DEG + SWEEP_HIGH_DEG) / 2 else SWEEP_LOW_DEG
    q1 = list(q0)
    q1[0] = math.radians(target_deg)
    print(f"sweep j1: {j1_deg:.2f} -> {target_deg:.2f} deg")

    # Cosine ease-in/out: zero start/end velocity. Peak vel = dist*pi/(2T),
    # peak acc = dist*(pi/T)^2/2 — size T to respect VMAX/AMAX with margin.
    dist = abs(q1[0] - q0[0])
    t_vel = dist * math.pi / (2 * VMAX[0] * 0.8)
    t_acc = math.sqrt(dist * math.pi**2 / (2 * AMAX[0] * 0.8))
    duration = max(t_vel, t_acc, 0.5)
    n = max(int(duration / DT), 100)
    traj = []
    for i in range(n):
        s = (1 - math.cos(math.pi * i / (n - 1))) / 2
        traj.append([a + (b - a) * s for a, b in zip(q0, q1)])
    print(f"trajectory: {n} samples, {duration:.2f}s nominal")

    try:
        mc.pathBufferFree(BUF)
    except Exception:
        pass
    mc.pathBufferAlloc(BUF, 2, len(traj))
    for i in range(0, len(traj), 50):
        mc.pathBufferAppend(BUF, traj[i : i + 50])
    mc.pathBufferEval(BUF, AMAX, VMAX, DT)
    while not mc.pathBufferValid(BUF):
        time.sleep(0.01)
    mc.movePathBuffer(BUF)

    t0 = time.monotonic()
    while mc.getExecId() == -1:
        if time.monotonic() - t0 > 5:
            raise SystemExit("motion never started")
        time.sleep(0.01)
    time.sleep(STOP_AFTER_S)

    q_now = list(state.getJointPositions())
    t_stop = time.monotonic()
    try:
        rc = apply_candidate(candidate, mc, q_now)
    except Exception as exc:
        rc = f"EXC {exc}"
    print(f"{candidate}: rc={rc} (fired at j1={math.degrees(q_now[0]):.2f} deg)")

    last = list(state.getJointPositions())
    t_still = None
    while time.monotonic() - t_stop < 8.0:
        time.sleep(0.05)
        cur = list(state.getJointPositions())
        if max(abs(a - b) for a, b in zip(cur, last)) < STILL_EPS_RAD:
            t_still = time.monotonic() - t_stop
            break
        last = cur

    qf = list(state.getJointPositions())
    early = abs(qf[0] - q1[0]) > math.radians(3.0)
    print(f"time_to_standstill: {t_still:.3f}s" if t_still else "time_to_standstill: >8s")
    print(f"final j1: {math.degrees(qf[0]):.2f} deg (target {target_deg:.2f})")
    print(f"STOPPED EARLY: {early}")
    print("safety after:", state.getSafetyModeType())
    print("execId after:", mc.getExecId())

    unlock_if_protective(state, rm)
    mc.setSpeedFraction(sf)
    rpc.logout()
    rpc.disconnect()


if __name__ == "__main__":
    main()
