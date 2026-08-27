"""wfctl — CLI test client for the WF bus (phase-1 arm vertical slice).

Shared flags: --realm (default live), --rid (default r1), --connect
<endpoint> (optional; default zenoh peer config which works when the driver
runs on the same LAN segment; with --connect, multicast scouting is off).
"""

from __future__ import annotations

import argparse
import json
import os
import math
import sys
import time
import uuid
from pathlib import Path

import yaml
import zenoh

from wf.core.cad_object import ObjectDef, instantiate

from wf.contracts.arm import keys
from wf.contracts.arm.messages import (
    Ack,
    ArmStatus,
    ExecutePathGoal,
    JogCommand,
    SetDo,
    Waypoint,
)
from wf.contracts.camera2d import keys as cam_keys
from wf.contracts.control import keys as control_keys
from wf.contracts.dio import keys as dio_keys
from wf.contracts.program import keys as program_keys
from wf.contracts.tags import keys as tags_keys
from wf.contracts.washer import keys as washer_keys
from wf.contracts.washer.messages import Ack as WasherAck
from wf.contracts.washer.messages import Recipe, RecipeReply, SetRecipe, WasherStatus
from wf.core.action import ActionClient, ActionRejected
from wf.contracts.tags.messages import Ack as TagsAck
from wf.contracts.tags.messages import ForceTag, TagsState, WriteTag
from wf.contracts.program.messages import Ack as ProgramAck
from wf.contracts.program.messages import Catalog, EventRequest, LoadRequest, LogLine, ProgramState
from wf.contracts.dio.messages import ForceChannel, SetChannel
from wf.contracts.dio.messages import Ack as DioAck
from wf.contracts.control.messages import AcquireControl, ControlAck
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
        # client mode: a peer would gossip host locators unreachable from Docker
        config.insert_json5("mode", json.dumps("client"))
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
    # Cell-level lease (one holder for every device), served by the supervisor.
    reply = _query(
        session,
        control_keys.cmd_acquire(args.realm),
        AcquireControl(client_id=client_id, user=user).to_wire(),
    )
    if reply is None:
        return ControlAck(ok=False, error="no_reply")
    return ControlAck.from_wire(reply)


def _release_lease(session, args, client_id: str) -> None:
    _query(
        session,
        control_keys.cmd_release(args.realm),
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


def _parse_channel_value(text: str):
    """``on``/``off``/``true``/``false``/``1``/``0`` -> bool; else float."""
    low = text.strip().lower()
    if low in ("on", "true", "1"):
        return True
    if low in ("off", "false", "0"):
        return False
    return float(text)


def _kv_pairs(items) -> dict:
    """``["k=v", ...]`` -> dict; values parsed as JSON when possible."""
    import json as _json

    out: dict = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"expected key=value, got {item!r}")
        k, v = item.split("=", 1)
        try:
            out[k] = _json.loads(v)
        except ValueError:
            out[k] = v
    return out


def cmd_program_catalog(session, args) -> int:
    reply = _query(session, program_keys.catalog(args.realm), {})
    if reply is None:
        print("no reply from programs/catalog (runner down?)", file=sys.stderr)
        return 1
    cat = Catalog.from_wire(reply)
    for entry in cat.programs:
        if entry.error:
            print(f"{entry.name:20s} BROKEN  {entry.error.splitlines()[-1]}")
        else:
            roles = ", ".join(f"{r}:{c}" for r, c in entry.roles.items())
            print(f"{entry.name:20s} roles[{roles}] params={entry.params}")
            if entry.doc:
                print(f"{'':20s} {entry.doc.splitlines()[0]}")
    return 0


def cmd_program_load(session, args) -> int:
    req = LoadRequest(name=args.name, bindings=_kv_pairs(args.bind), params=_kv_pairs(args.param))
    reply = _query(session, program_keys.cmd_load(args.realm), req.to_wire())
    if reply is None:
        print("no reply from programs/cmd/load", file=sys.stderr)
        return 1
    ack = ProgramAck.from_wire(reply)
    print("loaded" if ack.ok else f"error: {ack.error}")
    return 0 if ack.ok else 1


def cmd_program(session, args) -> int:
    payload = {"reason": args.reason} if args.reason else {}
    reply = _query(session, program_keys.cmd(args.realm, args.command), payload)
    if reply is None:
        print(f"no reply from program/cmd/{args.command}", file=sys.stderr)
        return 1
    ack = ProgramAck.from_wire(reply)
    print("ok" if ack.ok else f"error: {ack.error}")
    return 0 if ack.ok else 1


def cmd_program_event(session, args) -> int:
    reply = _query(
        session,
        program_keys.cmd_event(args.realm),
        EventRequest(event=args.event, data=_kv_pairs(args.data)).to_wire(),
    )
    if reply is None:
        print("no reply from program/cmd/event", file=sys.stderr)
        return 1
    ack = ProgramAck.from_wire(reply)
    print("ok" if ack.ok else f"error: {ack.error}")
    return 0 if ack.ok else 1


def cmd_program_state(session, args) -> int:
    def show(raw):
        st = ProgramState.from_wire(raw)
        line = f"unit={st.unit:12s} program={st.program or '-':16s} states={st.program_states} actions={st.actions}"
        if st.reason:
            line += f" reason={st.reason}"
        print(line)
        for w in st.waiting_for:
            if w.get("kind") == "channel":
                print(f"  waiting: {w.get('role')}.{w.get('channel')} {w.get('edge')} -> {w.get('event')} (-> {w.get('target')})")
            elif w.get("kind") == "timer":
                print(f"  waiting: after {w.get('seconds')}s in {w.get('state')} -> {w.get('event')} (-> {w.get('target')})")
            else:
                print(f"  accepts: event {w.get('event')!r} (-> {w.get('target')})")

    reply = _query(session, program_keys.state(args.realm), {})
    if reply is None:
        print("no reply from program/state (runner down?)", file=sys.stderr)
        return 1
    show(reply)
    if not args.follow:
        return 0
    sub = session.declare_subscriber(program_keys.state(args.realm), lambda s: show(decode(s.payload)))
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        sub.undeclare()
    return 0


def cmd_program_log(session, args) -> int:
    def show(raw):
        ln = LogLine.from_wire(raw)
        stamp = time.strftime("%H:%M:%S", time.localtime(ln.t / 1e9))
        print(f"{stamp} {ln.level:7s} {ln.source:12s} {ln.message}")

    reply = _query(session, program_keys.log(args.realm), {})
    if reply is None:
        print("no reply from program/log (runner down?)", file=sys.stderr)
        return 1
    for raw in reply.get("lines", [])[-args.tail:]:
        show(raw)
    if not args.follow:
        return 0
    sub = session.declare_subscriber(program_keys.log(args.realm), lambda s: show(decode(s.payload)))
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        sub.undeclare()
    return 0


def _parse_tag_value(text: str):
    """on/off/true/false -> bool; int -> int; float -> float; else string.
    ``--string`` keeps the text as-is."""
    low = text.strip().lower()
    if low in ("on", "true"):
        return True
    if low in ("off", "false"):
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


# ── host API (cells) — HTTP, no zenoh session needed ─────────────────────


def _http(method: str, url: str, body: dict | None = None) -> dict:
    import json as _json  # noqa: PLC0415
    import urllib.error  # noqa: PLC0415
    import urllib.request  # noqa: PLC0415

    data = None if body is None else _json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            return _json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as exc:
        try:
            detail = _json.loads(exc.read().decode()).get("detail")
        except Exception:
            detail = exc.reason
        raise SystemExit(f"host api {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"host api unreachable at {url}: {exc.reason}") from exc


def cmd_cell(args) -> int:
    base = args.host_api.rstrip("/")
    if args.action == "list":
        body = _http("GET", f"{base}/cells")
        active = (body.get("active") or {}).get("cell")
        for c in body["cells"]:
            mark = "*" if c["id"] == active else " "
            state = ""
            if c["id"] == active:
                state = f"  ACTIVE ({(body.get('active') or {}).get('runtime')}) {'alive' if body.get('alive') else 'DOWN'}"
            err = f"  ERROR {c['error']}" if c.get("error") else ""
            print(f"{mark} {c['id']:12s} {c['name']:20s} {c.get('cell_type') or '':22s} runtimes={','.join(c['runtimes'])}{state}{err}")
        return 0
    if args.action == "activate":
        if not args.cell:
            print("cell activate needs a cell id", file=sys.stderr)
            return 2
        body = _http("POST", f"{base}/cells/{args.cell}/activate", {"runtime": args.runtime})
        print(f"active: {body['active']}  alive={body['alive']}")
        return 0
    if args.action == "stop":
        body = _http("POST", f"{base}/cells/stop")
        print(f"active: {body['active']}")
        return 0
    if args.action == "health":
        print(json.dumps(_http("GET", f"{base}/health"), indent=2))
        return 0
    return 2


def cmd_washer_status(session, args) -> int:
    reply = _query(session, washer_keys.state_status(args.realm, args.washer), {})
    if reply is None:
        print("no reply from washer state/status (device down?)", file=sys.stderr)
        return 1
    st = WasherStatus.from_wire(reply)
    print(f"phase      {st.phase}")
    print(f"door       {st.door}")
    print(f"connected  {st.connected}   auto {st.auto}   fault {st.fault} (#{st.fault_code})")
    print(f"program    {st.program!r} #{st.program_no}")
    print(f"flags      ready_to_load={st.ready_to_load} ready_to_unload={st.ready_to_unload} washing={st.washing}")
    if st.sequence:
        print(f"sequence   {st.sequence}  {st.detail}")
    return 0


def cmd_washer_action(session, args) -> int:
    external_cid = args.client_id
    cid = external_cid or str(uuid.uuid4())
    if external_cid is None:
        ack = _acquire_lease(session, args, cid)
        if not ack.ok:
            print(f"lease denied: {ack.error}", file=sys.stderr)
            return 1
    try:
        goal = {"client_id": cid}
        if args.action == "start_wash" and args.program is not None:
            goal["program"] = int(args.program)
        client = ActionClient(session, washer_keys.action_prefix(args.realm, args.washer), args.action)
        try:
            g = client.send(goal, on_feedback=lambda fb: print(f"  … {fb.get('data', {}).get('step', '')} {fb.get('progress', 0):.0%}"))
        except ActionRejected as exc:
            print(f"rejected: {exc.reason}", file=sys.stderr)
            return 1
        print(f"goal {g.goal_id} accepted; waiting (Ctrl-C cancels = stop door)")
        try:
            result = g.result(timeout_s=float(args.timeout))
        except KeyboardInterrupt:
            g.cancel()
            print("cancelled: door permission released")
            return 130
        print(f"{result.get('state')}" + (f": {result.get('error')}" if result.get("error") else ""))
        return 0 if result.get("state") == "succeeded" else 1
    finally:
        if external_cid is None:
            _release_lease(session, args, cid)


def cmd_washer_stop_door(session, args) -> int:
    external_cid = args.client_id
    cid = external_cid or str(uuid.uuid4())
    if external_cid is None:
        ack = _acquire_lease(session, args, cid)
        if not ack.ok:
            print(f"lease denied: {ack.error}", file=sys.stderr)
            return 1
    try:
        reply = _query(session, washer_keys.cmd_stop_door(args.realm, args.washer), {"client_id": cid})
    finally:
        if external_cid is None:
            _release_lease(session, args, cid)
    if reply is None:
        print("no reply", file=sys.stderr)
        return 1
    ack = WasherAck.from_wire(reply)
    print("ok" if ack.ok else f"error: {ack.error}")
    return 0 if ack.ok else 1


def cmd_washer_recipe(session, args) -> int:
    if args.set is None:
        reply = _query(session, washer_keys.cmd_get_recipe(args.realm, args.washer), {})
        if reply is None:
            print("no reply", file=sys.stderr)
            return 1
        rr = RecipeReply.from_wire(reply)
        if not rr.ok or rr.recipe is None:
            print(f"error: {rr.error}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(rr.recipe.to_wire(), indent=2))
            return 0
        r = rr.recipe
        print(f"recipe {r.name!r}")
        print("  #  cleaning  time_s  movement  additional  pump_off")
        for i, st in enumerate(r.steps):
            if st.cleaning == 0 and st.time_s == 0:
                continue
            print(f"  {i + 1:<2} {st.cleaning:>8}  {st.time_s:>6}  {st.movement:>8}  {st.additional:>10}  {st.pump_off}")
        for k, v in r.params.items():
            spec = rr.schema.params.get(k) if rr.schema else None
            print(f"  {k:24s} {v:>6}  {spec.title if spec else ''}")
        return 0
    recipe = Recipe.from_wire(json.loads(Path(args.set).read_text(encoding="utf-8")))
    external_cid = args.client_id
    cid = external_cid or str(uuid.uuid4())
    if external_cid is None:
        ack = _acquire_lease(session, args, cid)
        if not ack.ok:
            print(f"lease denied: {ack.error}", file=sys.stderr)
            return 1
    try:
        reply = _query(session, washer_keys.cmd_set_recipe(args.realm, args.washer), SetRecipe(cid, recipe).to_wire(), timeout_s=15.0)
    finally:
        if external_cid is None:
            _release_lease(session, args, cid)
    if reply is None:
        print("no reply", file=sys.stderr)
        return 1
    ack = WasherAck.from_wire(reply)
    print("ok" if ack.ok else f"error: {ack.error}")
    return 0 if ack.ok else 1


def cmd_tags_state(session, args) -> int:
    reply = _query(session, tags_keys.state_tags(args.realm, args.tags), {})
    if reply is None:
        print("no reply from tags state/tags (device down?)", file=sys.stderr)
        return 1
    st = TagsState.from_wire(reply)
    for name, tv in sorted(st.tags.items()):
        flag = "  FORCED" if tv.forced else ""
        auto = "  (auto)" if tv.auto else ""
        addr = tv.address.get("node") or tv.address.get("tag") or ""
        print(f"{name:28s} {tv.type:6s} {tv.access:2s} {tv.value!s:>12}  {addr}{flag}{auto}")
    return 0


def _tags_cmd(session, args, key, msg_ok):
    external_cid = args.client_id
    cid = external_cid or str(uuid.uuid4())
    if external_cid is None:
        ack = _acquire_lease(session, args, cid)
        if not ack.ok:
            print(f"lease denied: {ack.error}", file=sys.stderr)
            return 1
    try:
        reply = _query(session, key, msg_ok(cid))
    finally:
        if external_cid is None:
            _release_lease(session, args, cid)
    if reply is None:
        print(f"no reply from {key}", file=sys.stderr)
        return 1
    ack = TagsAck.from_wire(reply)
    print("ok" if ack.ok else f"error: {ack.error}")
    return 0 if ack.ok else 1


def cmd_tags_write(session, args) -> int:
    value = args.value if args.string else _parse_tag_value(args.value)
    return _tags_cmd(session, args, tags_keys.cmd_write(args.realm, args.tags),
                     lambda cid: WriteTag(cid, args.tag, value).to_wire())


def cmd_tags_force(session, args) -> int:
    if not args.clear and args.value is None:
        print("tags-force needs a value or --clear", file=sys.stderr)
        return 2
    value = None if args.clear else (args.value if args.string else _parse_tag_value(args.value))
    # read-only tags need no lease: try lease-free first
    reply = _query(session, tags_keys.cmd_force(args.realm, args.tags), ForceTag(args.client_id or "wfctl", args.tag, value).to_wire())
    if reply is not None and reply.get("ok"):
        print("ok")
        return 0
    if reply is not None and reply.get("error") != "no_control":
        print(f"error: {reply.get('error')}")
        return 1
    return _tags_cmd(session, args, tags_keys.cmd_force(args.realm, args.tags),
                     lambda cid: ForceTag(cid, args.tag, value).to_wire())


def cmd_dio_state(session, args) -> int:
    reply = _query(session, dio_keys.state_channels(args.realm, args.dio), {})
    if reply is None:
        print("no reply from dio state/channels (device down?)", file=sys.stderr)
        return 1
    for name, cv in sorted(reply.get("channels", {}).items()):
        flag = "  FORCED" if cv.get("forced") else ""
        print(f"{name:20s} {cv['kind']:3s} {cv['value']!s:>8}{flag}")
    return 0


def cmd_dio_set(session, args) -> int:
    external_cid = args.client_id
    cid = external_cid or str(uuid.uuid4())
    if external_cid is None:
        ack = _acquire_lease(session, args, cid)
        if not ack.ok:
            print(f"lease denied: {ack.error}", file=sys.stderr)
            return 1
    try:
        req = SetChannel(client_id=cid, channel=args.channel, value=_parse_channel_value(args.value))
        reply = _query(session, dio_keys.cmd_set(args.realm, args.dio), req.to_wire())
    finally:
        if external_cid is None:
            _release_lease(session, args, cid)
    if reply is None:
        print("no reply from dio cmd/set", file=sys.stderr)
        return 1
    ack = DioAck.from_wire(reply)
    print("ok" if ack.ok else f"error: {ack.error}")
    return 0 if ack.ok else 1


def cmd_dio_force(session, args) -> int:
    if not args.clear and args.value is None:
        print("dio-force needs a value or --clear", file=sys.stderr)
        return 2
    value = None if args.clear else _parse_channel_value(args.value)
    external_cid = args.client_id

    def attempt(cid: str):
        req = ForceChannel(client_id=cid, channel=args.channel, value=value)
        return _query(session, dio_keys.cmd_force(args.realm, args.dio), req.to_wire())

    # Forcing an INPUT needs no lease (flagged test override); try that first so
    # it works while a program holds the cell lease. Outputs fall back to a
    # lease-acquiring attempt.
    reply = attempt(external_cid or "wfctl")
    if reply is not None and not reply.get("ok") and reply.get("error") == "no_control" and external_cid is None:
        cid = str(uuid.uuid4())
        ack = _acquire_lease(session, args, cid)
        if not ack.ok:
            print(f"lease denied: {ack.error}", file=sys.stderr)
            return 1
        try:
            reply = attempt(cid)
        finally:
            _release_lease(session, args, cid)
    if reply is None:
        print("no reply from dio cmd/force", file=sys.stderr)
        return 1
    ack = DioAck.from_wire(reply)
    print("ok" if ack.ok else f"error: {ack.error}")
    return 0 if ack.ok else 1


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
        control_keys.cmd_release(args.realm),
        {"client_id": args.client_id},
    )
    if reply is None:
        print("no reply from control/cmd/release", file=sys.stderr)
        return 1
    ack = ControlAck.from_wire(reply)
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

    p = sub.add_parser("acquire-control", help="acquire the cell control lease (all devices)")
    p.add_argument("--user", default="wfctl", help="operator label for the lease")
    p.add_argument("--client-id", default=None, help="reuse a client id (default: new uuid)")
    p.set_defaults(fn=cmd_acquire_control)

    p = sub.add_parser("release-control", help="release the cell control lease")
    p.add_argument("--client-id", required=True, help="the holding client id")
    p.set_defaults(fn=cmd_release_control)

    p = sub.add_parser("program-catalog", help="list discoverable programs")
    p.set_defaults(fn=cmd_program_catalog)

    p = sub.add_parser("program-load", help="load a program into the unit (Idle/Stopped)")
    p.add_argument("name")
    p.add_argument("--bind", action="append", metavar="ROLE=RID", help="bind a role to a device id")
    p.add_argument("--param", action="append", metavar="KEY=VALUE", help="override a param (JSON value)")
    p.set_defaults(fn=cmd_program_load)

    p = sub.add_parser("program", help="send a PackML unit command")
    p.add_argument("command", choices=program_keys.UNIT_COMMANDS)
    p.add_argument("--reason", default=None, help="reason (stop/abort)")
    p.set_defaults(fn=cmd_program)

    p = sub.add_parser("program-event", help="send an event to the running program")
    p.add_argument("event")
    p.add_argument("--data", action="append", metavar="KEY=VALUE")
    p.set_defaults(fn=cmd_program_event)

    p = sub.add_parser("program-state", help="print the unit/program state")
    p.add_argument("--follow", "-f", action="store_true", help="keep printing updates")
    p.set_defaults(fn=cmd_program_state)

    p = sub.add_parser("program-log", help="print the program/runner log")
    p.add_argument("--tail", type=int, default=50, help="last N lines (default 50)")
    p.add_argument("--follow", "-f", action="store_true", help="keep printing new lines")
    p.set_defaults(fn=cmd_program_log)

    p = sub.add_parser("cell", help="host API: list / activate / stop the cell running on this host")
    p.add_argument("action", choices=("list", "activate", "stop", "health"))
    p.add_argument("cell", nargs="?", default=None, help="cell id (activate)")
    p.add_argument("--runtime", default=None, help="overlay id (activate; default: 'default' or the first)")
    p.add_argument("--host-api", default=os.environ.get("WF_HOST_API", "http://127.0.0.1:8080"))
    p.set_defaults(fn=cmd_cell, no_session=True)

    p = sub.add_parser("washer-status", help="print a washer's phase/door/program")
    p.add_argument("--washer", default="washer0", help="washer resource id (default washer0)")
    p.set_defaults(fn=cmd_washer_status)

    p = sub.add_parser("washer", help="run a washer action (auto-acquires the lease; Ctrl-C cancels)")
    p.add_argument("action", choices=washer_keys.ACTIONS)
    p.add_argument("--program", default=None, help="wash program number (start_wash)")
    p.add_argument("--timeout", default=300.0)
    p.add_argument("--washer", default="washer0")
    p.add_argument("--client-id", default=None, help="reuse an external lease")
    p.set_defaults(fn=cmd_washer_action)

    p = sub.add_parser("washer-stop-door", help="release the door permission (a travelling door stops)")
    p.add_argument("--washer", default="washer0")
    p.add_argument("--client-id", default=None)
    p.set_defaults(fn=cmd_washer_stop_door)

    p = sub.add_parser("washer-recipe", help="print the machine's wash program, or --set it from a JSON file")
    p.add_argument("--set", default=None, metavar="FILE.json")
    p.add_argument("--json", action="store_true", help="print as JSON (round-trips with --set)")
    p.add_argument("--washer", default="washer0")
    p.add_argument("--client-id", default=None)
    p.set_defaults(fn=cmd_washer_recipe)

    p = sub.add_parser("tags-state", help="print a tags device's variables")
    p.add_argument("--tags", default="plc0", help="tags resource id (default plc0)")
    p.set_defaults(fn=cmd_tags_state)

    p = sub.add_parser("tags-write", help="write a rw tag (auto-acquires the lease)")
    p.add_argument("tag")
    p.add_argument("value")
    p.add_argument("--string", action="store_true", help="keep the value as a string")
    p.add_argument("--tags", default="plc0", help="tags resource id (default plc0)")
    p.add_argument("--client-id", default=None, help="reuse an external lease")
    p.set_defaults(fn=cmd_tags_write)

    p = sub.add_parser("tags-force", help="force a tag's reported value (read-only tags need no lease)")
    p.add_argument("tag")
    p.add_argument("value", nargs="?", default=None)
    p.add_argument("--clear", action="store_true")
    p.add_argument("--string", action="store_true")
    p.add_argument("--tags", default="plc0", help="tags resource id (default plc0)")
    p.add_argument("--client-id", default=None)
    p.set_defaults(fn=cmd_tags_force)

    p = sub.add_parser("dio-state", help="print a dio device's named channels")
    p.add_argument("--dio", default="io0", help="dio resource id (default io0)")
    p.set_defaults(fn=cmd_dio_state)

    p = sub.add_parser("dio-set", help="set a dio OUTPUT channel (auto-acquires the lease)")
    p.add_argument("channel")
    p.add_argument("value", help="on|off|true|false|1|0 or a number")
    p.add_argument("--dio", default="io0", help="dio resource id (default io0)")
    p.add_argument("--client-id", default=None, help="reuse an external lease")
    p.set_defaults(fn=cmd_dio_set)

    p = sub.add_parser("dio-force", help="force ANY dio channel's reported value (auto-acquires the lease)")
    p.add_argument("channel")
    p.add_argument("value", nargs="?", default=None, help="on|off|true|false|1|0 or a number")
    p.add_argument("--clear", action="store_true", help="clear the force instead")
    p.add_argument("--dio", default="io0", help="dio resource id (default io0)")
    p.add_argument("--client-id", default=None, help="reuse an external lease")
    p.set_defaults(fn=cmd_dio_force)

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
    if getattr(args, "no_session", False):
        return args.fn(args)
    session = _open_session(args)
    try:
        return args.fn(session, args)
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
