"""wfctl — CLI test client for the WF bus (phase-1 arm vertical slice).

Shared flags: --realm (default live), --rid (default r1), --connect
<endpoint> (optional; default zenoh peer config which works when the driver
runs on the same LAN segment; with --connect, multicast scouting is off).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import uuid

import yaml
import zenoh

from wf.core.cad_object import ObjectDef, instantiate

from wf.contracts.arm import keys
from wf.contracts.arm.messages import (
    Ack,
    AcquireControl,
    ArmStatus,
    ControlAck,
    ExecutePathGoal,
    JogCommand,
    SetDo,
    Waypoint,
)
from wf.contracts.camera2d import keys as cam_keys
from wf.contracts.camera2d.messages import Ack as CamAck
from wf.contracts.camera2d.messages import GrabReply
from wf.core.action import ActionClient, ActionRejected
from wf.core.codec import decode, encode
from wf.core.frames import rotation_matrix_to_quaternion, rpy_to_matrix
from wf.core.keys import realm_prefix
from wf.services.config import keys as config_keys
from wf.services.recording import keys as recording_keys


def _open_session(args) -> zenoh.Session:
    if args.connect:
        config = zenoh.Config()
        config.insert_json5("mode", json.dumps("peer"))
        config.insert_json5("scouting/multicast/enabled", "false")
        config.insert_json5("connect/endpoints", json.dumps([args.connect]))
    else:
        config = zenoh.Config()
    session = zenoh.open(config)
    # Give routes a moment to propagate.
    time.sleep(0.5)
    return session


def _full_key(args, suffix: str) -> str:
    head = suffix.split("/", 1)[0]
    try:
        realm_prefix(head if head != "replay" else suffix)
        return suffix  # already a full key with a realm prefix
    except ValueError:
        return f"{keys.prefix(args.realm, args.rid)}/{suffix}"


def _query(session, key: str, payload: dict, timeout_s: float = 5.0) -> dict | None:
    replies = session.get(key, payload=encode(payload), timeout=timeout_s)
    for reply in replies:
        if reply.ok is not None:
            return decode(reply.ok.payload)
    return None


def _query_all(session, selector: str, timeout_s: float = 5.0) -> dict[str, dict]:
    replies = session.get(selector, payload=encode({}), timeout=timeout_s)
    out: dict[str, dict] = {}
    for reply in replies:
        if reply.ok is not None:
            out[str(reply.ok.key_expr)] = decode(reply.ok.payload)
    return out


def cmd_sub(session, args) -> int:
    key = _full_key(args, args.key_suffix)
    count = 0
    rate_count = 0
    t0 = time.monotonic()
    done = False

    def on_sample(sample):
        nonlocal count, rate_count, done
        if done:
            return
        count += 1
        rate_count += 1
        if not args.rate:
            try:
                print(json.dumps(decode(sample.payload)), flush=True)
            except Exception as exc:
                print(f"<decode error: {exc!r}>", file=sys.stderr)
        if args.count and count >= args.count:
            done = True

    sub = session.declare_subscriber(key, on_sample)
    print(f"subscribed to {key}", file=sys.stderr)
    try:
        while not done:
            time.sleep(0.1)
            if args.rate:
                elapsed = time.monotonic() - t0
                if elapsed >= 1.0:
                    print(f"{rate_count / elapsed:.1f} Hz", flush=True)
                    rate_count = 0
                    t0 = time.monotonic()
    except KeyboardInterrupt:
        pass
    finally:
        sub.undeclare()
    return 0


def cmd_status(session, args) -> int:
    result: list[dict] = []

    def on_sample(sample):
        if not result:
            result.append(decode(sample.payload))

    sub = session.declare_subscriber(keys.state_status(args.realm, args.rid), on_sample)
    try:
        deadline = time.monotonic() + args.timeout
        while not result and time.monotonic() < deadline:
            time.sleep(0.05)
    finally:
        sub.undeclare()
    if not result:
        print(f"no ArmStatus within {args.timeout}s", file=sys.stderr)
        return 1
    status = ArmStatus.from_wire(result[0])
    print(json.dumps(status.to_wire(), indent=2))
    return 0


def cmd_set_do(session, args) -> int:
    req = SetDo(bank=args.bank, pin=args.pin, value=bool(args.value))
    reply = _query(session, keys.cmd_set_do(args.realm, args.rid), req.to_wire())
    if reply is None:
        print("no reply from cmd/set_do", file=sys.stderr)
        return 1
    ack = Ack.from_wire(reply)
    print(json.dumps(ack.to_wire()))
    return 0 if ack.ok else 1


def _parse_joints(args) -> list[float]:
    spec = args.deg if args.deg is not None else args.rad
    values = [float(v.strip()) for v in spec.split(",")]
    if len(values) != 6:
        raise SystemExit(f"expected 6 joint values, got {len(values)}")
    if args.deg is not None:
        values = [math.radians(v) for v in values]
    return values


def _parse_xyz(spec: str) -> list[float]:
    values = [float(v.strip()) for v in spec.split(",")]
    if len(values) != 3:
        raise SystemExit(f"expected 3 xyz values, got {len(values)}")
    return values


def _pose_args_to_quat(args) -> list[float]:
    if args.quat is not None:
        values = [float(v.strip()) for v in args.quat.split(",")]
        if len(values) != 4:
            raise SystemExit(f"expected 4 quat values, got {len(values)}")
        return values
    if args.rpy_deg is not None:
        rpy = [math.radians(float(v.strip())) for v in args.rpy_deg.split(",")]
        if len(rpy) != 3:
            raise SystemExit(f"expected 3 rpy values, got {len(rpy)}")
        return rotation_matrix_to_quaternion(rpy_to_matrix(rpy))
    return [0.0, 0.0, 0.0, 1.0]


def _acquire_lease(session, args, client_id: str, user: str = "wfctl") -> ControlAck:
    reply = _query(
        session,
        keys.cmd_acquire_control(args.realm, args.rid),
        AcquireControl(client_id=client_id, user=user).to_wire(),
    )
    if reply is None:
        return ControlAck(ok=False, error="no_reply")
    return ControlAck.from_wire(reply)


def _release_lease(session, args, client_id: str) -> None:
    _query(
        session,
        keys.cmd_release_control(args.realm, args.rid),
        {"client_id": client_id},
    )


def _send_goal(session, args, waypoints: list[Waypoint]) -> int:
    # Auto-acquire the control lease unless an external --client-id is reused.
    external_cid = getattr(args, "client_id", None)
    cid = external_cid or str(uuid.uuid4())
    owned = external_cid is None
    if owned:
        ack = _acquire_lease(session, args, cid)
        if not ack.ok:
            print(f"control lease unavailable: {ack.error}", file=sys.stderr)
            return 1

    goal_msg = ExecutePathGoal(waypoints=waypoints, client_id=cid)
    client = ActionClient(
        session, keys.action_prefix(args.realm, args.rid), "execute_path"
    )

    def on_feedback(fb: dict):
        print(
            f"feedback state={fb.get('state')} progress={fb.get('progress'):.3f} "
            f"data={json.dumps(fb.get('data'))}",
            flush=True,
        )

    try:
        try:
            goal = client.send(
                goal_msg.to_wire(), goal_id=args.goal_id, on_feedback=on_feedback
            )
        except ActionRejected as exc:
            print(f"rejected: {exc.reason}", file=sys.stderr)
            return 1
        print(f"accepted goal_id={goal.goal_id}", flush=True)
        result = goal.result(timeout_s=120.0)
        print(json.dumps(result))
        return 0 if result.get("state") == "succeeded" else 1
    finally:
        if owned:
            _release_lease(session, args, cid)


def cmd_movej(session, args) -> int:
    if args.pose is not None:
        reply = _query(session, config_keys.pose(args.pose), {})
        if reply is None:
            print("pose not found (config service running?)", file=sys.stderr)
            return 1
        q = [float(v) for v in reply["q"]]
    else:
        q = _parse_joints(args)
    return _send_goal(session, args, [Waypoint(type="movej", target={"q": q})])


def cmd_movep(session, args) -> int:
    xyz = _parse_xyz(args.xyz)
    quat = _pose_args_to_quat(args)
    wp = Waypoint(
        type="movej",
        target={"pose": {"frame": args.frame, "xyz": xyz, "quat": quat}},
    )
    return _send_goal(session, args, [wp])


def cmd_cancel(session, args) -> int:
    reply = _query(
        session,
        f"{keys.action_prefix(args.realm, args.rid)}/cancel",
        {"goal_id": args.goal_id},
    )
    if reply is None:
        print("no reply from action/cancel", file=sys.stderr)
        return 1
    print(json.dumps(reply))
    return 0


def cmd_stop(session, args) -> int:
    reply = _query(session, keys.cmd_stop(args.realm, args.rid), {})
    if reply is None:
        print("no reply from cmd/stop", file=sys.stderr)
        return 1
    ack = Ack.from_wire(reply)
    print(json.dumps(ack.to_wire()))
    return 0 if ack.ok else 1


def cmd_clear_pstop(session, args) -> int:
    reply = _query(
        session, keys.cmd_clear_protective_stop(args.realm, args.rid), {}
    )
    if reply is None:
        print("no reply from cmd/clear_protective_stop", file=sys.stderr)
        return 1
    ack = Ack.from_wire(reply)
    print(json.dumps(ack.to_wire()))
    return 0 if ack.ok else 1


_CART_AXES = {"x": 0, "y": 1, "z": 2, "rx": 3, "ry": 4, "rz": 5}


def cmd_acquire_control(session, args) -> int:
    cid = args.client_id or str(uuid.uuid4())
    ack = _acquire_lease(session, args, cid, user=args.user)
    if ack.ok:
        print(f"client_id={cid}")
        if ack.owner is not None:
            print(f"granted to {ack.owner.user} (expires_at={ack.owner.expires_at})")
        return 0
    print(f"denied: {ack.error}", file=sys.stderr)
    if ack.owner is not None:
        print(f"held by {ack.owner.user}", file=sys.stderr)
    return 1


def cmd_release_control(session, args) -> int:
    reply = _query(
        session,
        keys.cmd_release_control(args.realm, args.rid),
        {"client_id": args.client_id},
    )
    if reply is None:
        print("no reply from cmd/release_control", file=sys.stderr)
        return 1
    ack = Ack.from_wire(reply)
    print("released" if ack.ok else f"error: {ack.error}")
    return 0 if ack.ok else 1


def cmd_jog(session, args) -> int:
    if args.joint is not None:
        if not 0 <= args.joint <= 5:
            print("--joint must be 0..5", file=sys.stderr)
            return 1
        mode = "joint"
        velocity = [0.0] * 6
        velocity[args.joint] = args.vel
    else:
        axis = args.cart.lower()
        if axis not in _CART_AXES:
            print("--cart must be one of x,y,z,rx,ry,rz", file=sys.stderr)
            return 1
        mode = "cartesian"
        velocity = [0.0] * 6
        velocity[_CART_AXES[axis]] = args.vel
    frame = args.frame

    external_cid = args.client_id
    cid = external_cid or str(uuid.uuid4())
    owned = external_cid is None
    if owned:
        ack = _acquire_lease(session, args, cid)
        if not ack.ok:
            print(f"control lease unavailable: {ack.error}", file=sys.stderr)
            return 1
        print(f"acquired control client_id={cid}")

    pub = session.declare_publisher(keys.cmd_jog(args.realm, args.rid))
    period = 1.0 / 15.0
    deadline = time.monotonic() + args.secs
    try:
        while time.monotonic() < deadline:
            cmd = JogCommand(
                client_id=cid, mode=mode, frame=frame,
                velocity=velocity, t=time.time_ns(),
            )
            pub.put(encode(cmd.to_wire()))
            time.sleep(period)
    finally:
        pub.undeclare()
        if owned:
            _release_lease(session, args, cid)
            print("released control")
    return 0


def cmd_set_tcp(session, args) -> int:
    reply = _query(session, keys.cmd_set_tcp(args.realm, args.rid), {"name": args.name})
    if reply is None:
        print("no reply from cmd/set_tcp", file=sys.stderr)
        return 1
    ack = Ack.from_wire(reply)
    print(json.dumps(ack.to_wire()))
    return 0 if ack.ok else 1


def cmd_pose(session, args) -> int:
    if args.action in ("save", "show") and not args.name:
        print(f"pose {args.action} requires a name", file=sys.stderr)
        return 2
    if args.action == "save":
        result: list[dict] = []

        def on_sample(sample):
            if not result:
                result.append(decode(sample.payload))

        sub = session.declare_subscriber(
            keys.state_joints(args.realm, args.rid), on_sample
        )
        try:
            deadline = time.monotonic() + 2.0
            while not result and time.monotonic() < deadline:
                time.sleep(0.05)
        finally:
            sub.undeclare()
        if not result:
            print("no joints sample within 2.0s", file=sys.stderr)
            return 1
        q = [float(v) for v in result[0]["q"]]
        reply = _query(
            session,
            config_keys.cmd_set(),
            {"key": config_keys.pose(args.name), "value": {"q": q, "meta": {}}},
        )
        if reply is None:
            print(
                "no reply from config/cmd/set (config service running?)",
                file=sys.stderr,
            )
            return 1
        print(json.dumps(reply))
        return 0 if reply.get("ok") else 1
    if args.action == "list":
        entries = _query_all(session, config_keys.poses_glob())
        for key_str in sorted(entries):
            name = key_str.removeprefix("config/poses/")
            q_deg = ", ".join(
                f"{math.degrees(float(v)):.2f}" for v in entries[key_str].get("q", [])
            )
            print(f"{name}  {q_deg}")
        return 0
    # show
    reply = _query(session, config_keys.pose(args.name), {})
    if reply is None:
        print("pose not found", file=sys.stderr)
        return 1
    print(json.dumps(reply, indent=2))
    return 0


def cmd_frame(session, args) -> int:
    if args.action in ("show", "set") and not args.name:
        print(f"frame {args.action} requires a name", file=sys.stderr)
        return 2
    if args.action == "list":
        entries = _query_all(session, config_keys.frames_glob())
        for key_str in sorted(entries):
            name = key_str.removeprefix("config/frames/")
            v = entries[key_str]
            xyz = ",".join(f"{float(c):.4f}" for c in v.get("xyz", []))
            quat = ",".join(f"{float(c):.4f}" for c in v.get("quat", []))
            print(
                f"{name}  parent={v.get('parent')}  xyz=[{xyz}]  quat=[{quat}]  "
                f"source={v.get('source')}  rev={v.get('revision')}"
            )
        return 0
    if args.action == "show":
        reply = _query(session, config_keys.frame(args.name), {})
        if reply is None:
            print("frame not found", file=sys.stderr)
            return 1
        print(json.dumps(reply, indent=2))
        return 0
    # set
    if not args.parent:
        print("frame set requires --parent", file=sys.stderr)
        return 2
    xyz = _parse_xyz(args.xyz)
    quat = _pose_args_to_quat(args)
    reply = _query(
        session,
        config_keys.cmd_set(),
        {
            "key": config_keys.frame(args.name),
            "value": {
                "parent": args.parent,
                "xyz": xyz,
                "quat": quat,
                "source": "manual",
                "meta": {},
            },
        },
    )
    if reply is None:
        print(
            "no reply from config/cmd/set (config service running?)", file=sys.stderr
        )
        return 1
    print(json.dumps(reply))
    return 0 if reply.get("ok") else 1


def cmd_tcp(session, args) -> int:
    entries = _query_all(session, config_keys.tcps_glob(args.rid))
    for key_str in sorted(entries):
        name = key_str.rsplit("/", 1)[-1]
        v = entries[key_str]
        xyz = ",".join(f"{float(c):.4f}" for c in v.get("xyz", []))
        quat = ",".join(f"{float(c):.4f}" for c in v.get("quat", []))
        print(
            f"{name}  role={v.get('role')}  selectable={v.get('selectable_as_tcp')}  "
            f"xyz=[{xyz}]  quat=[{quat}]"
        )
    return 0


def cmd_scene(session, args) -> int:
    if args.action == "show" and not args.name:
        print("scene show requires a name", file=sys.stderr)
        return 2
    if args.action == "show":
        reply = _query(session, config_keys.scene(args.name), {})
        if reply is None:
            print("scene object not found", file=sys.stderr)
            return 1
        print(json.dumps(reply, indent=2))
        return 0
    # list
    entries = _query_all(session, config_keys.scene_glob())
    for key_str in sorted(entries):
        name = key_str.removeprefix("config/scene/")
        v = entries[key_str]
        geom = v.get("geometry") or {}
        pose = v.get("pose") or {}
        xyz = ",".join(f"{float(c):.4f}" for c in pose.get("xyz", []))
        print(
            f"{name}  frame={v.get('frame')}  geometry={geom.get('type')}  "
            f"xyz=[{xyz}]  rev={v.get('revision')}"
        )
    return 0


def cmd_object(session, args) -> int:
    # only action is "import"
    try:
        with open(args.manifest) as f:
            raw = yaml.safe_load(f)
        obj = ObjectDef.from_wire(raw)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"failed to load object manifest: {exc}", file=sys.stderr)
        return 1
    frames, scene = instantiate(
        obj,
        instance=args.instance,
        parent_frame=args.frame,
        xyz=_parse_xyz(args.xyz),
        quat=_pose_args_to_quat(args),
    )
    from . import scene_import

    errors = scene_import.apply(
        frames, scene, session=session, realm=args.realm, mode=args.mode
    )
    for err in errors:
        print(err, file=sys.stderr)
    if errors:
        return 1
    print(
        f"imported {obj.name!r} as {args.instance!r} ({args.mode}): "
        f"{len(frames)} frame(s), {len(scene)} scene object(s)"
    )
    return 0


def cmd_record(session, args) -> int:
    if args.action == "mark" and not args.label:
        print("record mark requires a label", file=sys.stderr)
        return 2
    if args.action == "start":
        payload = {"realm": args.realm}
        if args.label:
            payload["label"] = args.label
    else:
        payload = {"label": args.label} if args.label else {}
    key = {
        "start": recording_keys.cmd_start(),
        "stop": recording_keys.cmd_stop(),
        "mark": recording_keys.cmd_mark(),
    }[args.action]
    reply = _query(session, key, payload)
    if reply is None:
        print(f"no reply from {key}", file=sys.stderr)
        return 1
    print(json.dumps(reply))
    return 0 if reply.get("ok") else 1


def cmd_replay(session, args) -> int:
    if args.action == "seek":
        if args.value is None:
            print("replay seek requires a data-time value in ns", file=sys.stderr)
            return 2
        payload = {"t_ns": int(args.value)}
    elif args.action == "rate":
        if args.value is None:
            print("replay rate requires a rate value", file=sys.stderr)
            return 2
        payload = {"rate": float(args.value)}
    else:
        payload = {}
    key = recording_keys.replay_cmd(args.session, args.action)
    reply = _query(session, key, payload)
    if reply is None:
        print(f"no reply from {key}", file=sys.stderr)
        return 1
    print(json.dumps(reply))
    return 0 if reply.get("ok") else 1


def cmd_cam_grab(session, args) -> int:
    spec: dict = {"encoding": "jpeg", "quality": args.quality, "scale": args.scale}
    if args.roi is not None:
        spec["roi"] = args.roi
    # A SingleFrame grab takes ~1 s; allow for it.
    reply = _query(
        session, cam_keys.cmd_grab(args.realm, args.cid), spec, timeout_s=10.0
    )
    if reply is None:
        print("no reply from cmd/grab", file=sys.stderr)
        return 1
    grab = GrabReply.from_wire(reply)
    if not grab.ok or grab.data is None or grab.header is None:
        print(grab.error or "grab failed", file=sys.stderr)
        return 1
    with open(args.out, "wb") as f:
        f.write(grab.data)
    print(json.dumps(grab.header.to_wire()))
    print(f"wrote {len(grab.data)} bytes to {args.out}")
    return 0


def cmd_cam_stream(session, args) -> int:
    if args.action == "stop":
        key = cam_keys.cmd_stream_stop(args.realm, args.cid)
        reply = _query(session, key, {})
    else:
        # Send only the explicitly-passed fields; the driver merges them
        # over its cell.yaml stream_defaults.
        params: dict = {}
        if args.rate is not None:
            params["rate_hz"] = args.rate
        if args.scale is not None:
            params["scale"] = args.scale
        if args.quality is not None:
            params["quality"] = args.quality
        if args.roi is not None:
            params["roi"] = args.roi
        if args.raw:
            params["encoding"] = "BayerRG8"
        key = cam_keys.cmd_stream_start(args.realm, args.cid)
        reply = _query(session, key, params)
    if reply is None:
        print(f"no reply from {key}", file=sys.stderr)
        return 1
    ack = CamAck.from_wire(reply)
    print(json.dumps(ack.to_wire()))
    return 0 if ack.ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="wfctl", description=__doc__)
    parser.add_argument("--realm", default="cell")
    parser.add_argument("--rid", default="r1")
    parser.add_argument("--connect", default=None, help="zenoh endpoint, e.g. tcp/127.0.0.1:7447")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sub", help="subscribe to a state key and print samples")
    p.add_argument("key_suffix", help="key suffix (e.g. state/joints) or full key")
    p.add_argument("--count", type=int, default=0, help="exit after N samples")
    p.add_argument("--rate", action="store_true", help="print measured Hz instead of payloads")
    p.set_defaults(fn=cmd_sub)

    p = sub.add_parser("status", help="print the latest ArmStatus")
    p.add_argument("--timeout", type=float, default=3.0)
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("set-do", help="set a digital output")
    p.add_argument("--pin", type=int, required=True)
    p.add_argument("--value", type=int, choices=(0, 1), required=True)
    p.add_argument("--bank", choices=("standard", "tool"), default="standard")
    p.set_defaults(fn=cmd_set_do)

    p = sub.add_parser("movej", help="single-waypoint movej goal")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--deg", help='comma-separated degrees: "j0,j1,j2,j3,j4,j5"')
    group.add_argument("--rad", help="comma-separated radians")
    group.add_argument("--pose", help="stored pose name (config/poses/<name>)")
    p.add_argument("--goal-id", default=None, help="replay a goal id (idempotency test)")
    p.add_argument(
        "--client-id", default=None,
        help="reuse an external control lease (skip auto acquire/release)",
    )
    p.set_defaults(fn=cmd_movej)

    p = sub.add_parser("movep", help="frame-referenced pose-target movej goal")
    p.add_argument("--frame", required=True, help="reference frame name (config/frames/<name>)")
    p.add_argument("--xyz", required=True, help='position "x,y,z" in metres, in --frame')
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--quat", help='orientation "qx,qy,qz,qw"')
    group.add_argument("--rpy-deg", help='orientation "r,p,y" in degrees (extrinsic XYZ)')
    p.add_argument("--goal-id", default=None, help="replay a goal id (idempotency test)")
    p.add_argument(
        "--client-id", default=None,
        help="reuse an external control lease (skip auto acquire/release)",
    )
    p.set_defaults(fn=cmd_movep)

    p = sub.add_parser("pose", help="stored joint poses (config/poses/*)")
    p.add_argument("action", choices=("save", "list", "show"))
    p.add_argument("name", nargs="?", default=None)
    p.set_defaults(fn=cmd_pose)

    p = sub.add_parser("frame", help="static frames (config/frames/*)")
    p.add_argument("action", choices=("list", "show", "set"))
    p.add_argument("name", nargs="?", default=None)
    p.add_argument("--parent", default=None, help="parent frame name (frame set)")
    p.add_argument("--xyz", default="0,0,0", help='translation "x,y,z" in metres')
    group = p.add_mutually_exclusive_group()
    group.add_argument("--quat", help='rotation "qx,qy,qz,qw" (default identity)')
    group.add_argument("--rpy-deg", help='rotation "r,p,y" in degrees (extrinsic XYZ)')
    p.set_defaults(fn=cmd_frame)

    p = sub.add_parser("tcp", help="TCP definitions (config/arm/<rid>/tcp/*)")
    p.add_argument("action", choices=("list",))
    p.set_defaults(fn=cmd_tcp)

    p = sub.add_parser("scene", help="scene objects (config/scene/*)")
    p.add_argument("action", choices=("list", "show"))
    p.add_argument("name", nargs="?", default=None)
    p.set_defaults(fn=cmd_scene)

    p = sub.add_parser("object", help="import a CAD object manifest into frames+scene")
    p.add_argument("action", choices=("import",))
    p.add_argument("manifest", help="path to an ObjectDef YAML manifest")
    p.add_argument("--instance", required=True, help="instance id (root frame name)")
    p.add_argument("--frame", required=True, help="parent frame to place the instance in")
    p.add_argument("--xyz", default="0,0,0", help='instance position "x,y,z" in metres')
    group = p.add_mutually_exclusive_group()
    group.add_argument("--quat", help='instance orientation "qx,qy,qz,qw" (default identity)')
    group.add_argument("--rpy-deg", help='instance orientation "r,p,y" in degrees (extrinsic XYZ)')
    p.add_argument(
        "--mode", choices=("config", "live"), default="config",
        help="persist to the config store or publish to the runtime bus",
    )
    p.set_defaults(fn=cmd_object)

    p = sub.add_parser("set-tcp", help="select the driver's active TCP")
    p.add_argument("name", help='TCP name from the config store, or "flange"')
    p.set_defaults(fn=cmd_set_tcp)

    p = sub.add_parser("cancel", help="cancel a goal")
    p.add_argument("goal_id")
    p.set_defaults(fn=cmd_cancel)

    p = sub.add_parser("stop", help="out-of-band stop (aborts the active goal)")
    p.set_defaults(fn=cmd_stop)

    p = sub.add_parser("clear-pstop", help="unlock a protective stop (re-arm)")
    p.set_defaults(fn=cmd_clear_pstop)

    p = sub.add_parser("acquire-control", help="acquire the motion control lease")
    p.add_argument("--user", default="wfctl", help="operator label for the lease")
    p.add_argument("--client-id", default=None, help="reuse a client id (default: new uuid)")
    p.set_defaults(fn=cmd_acquire_control)

    p = sub.add_parser("release-control", help="release the motion control lease")
    p.add_argument("--client-id", required=True, help="the holding client id")
    p.set_defaults(fn=cmd_release_control)

    p = sub.add_parser("jog", help="hold-to-jog stream (auto-acquires the lease)")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--joint", type=int, metavar="J", help="joint index 0..5 (joint-space)")
    group.add_argument("--cart", metavar="AXIS", help="cartesian axis: x|y|z|rx|ry|rz")
    p.add_argument("--vel", type=float, required=True, help="velocity (rad/s joint; m/s|rad/s cart)")
    p.add_argument("--frame", default="base", help="reference frame: 'base'|'tool'|config frame name")
    p.add_argument("--secs", type=float, default=2.0, help="stream duration seconds")
    p.add_argument("--client-id", default=None, help="reuse an external lease (skip auto acquire/release)")
    p.set_defaults(fn=cmd_jog)

    p = sub.add_parser("record", help="control the recorder (recording/cmd/*)")
    p.add_argument("action", choices=("start", "stop", "mark"))
    p.add_argument("label", nargs="?", default=None, help="recording/mark label")
    p.set_defaults(fn=cmd_record)

    p = sub.add_parser("replay", help="control a replayer (replay/<id>/cmd/*)")
    p.add_argument("action", choices=("play", "pause", "seek", "rate", "info"))
    p.add_argument("value", nargs="?", default=None, help="seek t_ns or rate value")
    p.add_argument("--session", required=True, help="replay session id")
    p.set_defaults(fn=cmd_replay)

    p = sub.add_parser("cam-grab", help="grab one jpeg frame (cmd/grab)")
    p.add_argument("--cid", default="cam0")
    p.add_argument("--out", required=True, help="output jpeg file path")
    p.add_argument("--quality", type=int, default=95)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--roi", type=int, nargs=4, default=None, metavar=("X", "Y", "W", "H"))
    p.set_defaults(fn=cmd_cam_grab)

    p = sub.add_parser("cam-stream", help="start/stop the camera stream")
    p.add_argument("action", choices=("start", "stop"))
    p.add_argument("--cid", default="cam0")
    p.add_argument("--rate", type=float, default=None, help="rate_hz")
    p.add_argument("--scale", type=float, default=None)
    p.add_argument("--quality", type=int, default=None)
    p.add_argument("--roi", type=int, nargs=4, default=None, metavar=("X", "Y", "W", "H"))
    p.add_argument("--raw", action="store_true", help="encoding=BayerRG8 (default jpeg)")
    p.set_defaults(fn=cmd_cam_stream)

    args = parser.parse_args(argv)
    session = _open_session(args)
    try:
        return args.fn(session, args)
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
