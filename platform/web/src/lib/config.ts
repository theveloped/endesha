// Key space of the bus, as the UI consumes it. The builders themselves are
// GENERATED from the Python key modules (src/lib/gen/keys.ts — regenerate
// with `pixi run wiregen`, drift-gated by `pixi run wire-check`); this file
// is the thin hand-written adapter that keeps the UI's historical names,
// default ids (RID/CID/"main") and grouped conveniences. The realm is
// caller-supplied: every builder takes the full namespace prefix string
// ("cell" or "replay/{sid}") — the UI's switcher picks it and identical
// components render the live cell or a recording by prefix swap alone.
import * as gen from "./gen/keys";

export const RID = "r1";

export const DEFAULT_WS_URL = "ws/127.0.0.1:10000";

export const CELL_NAME = "dev-cell"; // no cell registry on the bus yet — constant

// The operating namespace is the single fixed token "cell": live/sim/replay is
// a per-device source mode, not a key prefix (RFC §3.1). "replay" here is the
// whole-session global replayer, which keeps its own replay/{sid} namespace.
export type RealmKind = "cell" | "replay";

export const CELL_REALM = "cell";

export interface Realm {
  kind: RealmKind;
  replaySession: string | null;
}

/** null while kind=replay and no session picked — subscribe nothing. */
export function realmPrefix(r: Realm): string | null {
  if (r.kind !== "replay") return CELL_REALM;
  return r.replaySession === null ? null : `replay/${r.replaySession}`;
}

export function replayCmd(sid: string, action: string): string {
  return gen.recordingReplayCmd(sid, action);
}

export function replayClock(sid: string): string {
  return gen.recordingReplayClock(sid);
}

/** Matches replay/{sid}/{contract}/{rid}/alive liveliness tokens. */
export const REPLAY_ALIVE_GLOB = "replay/*/*/*/alive";

// ── arm ──────────────────────────────────────────────────────────────────

export function stateJoints(realm: string, rid = RID): string {
  return gen.armStateJoints(realm, rid);
}

export function stateFlange(realm: string, rid = RID): string {
  return gen.armStateFlange(realm, rid);
}

export function stateTcp(realm: string, rid = RID): string {
  return gen.armStateTcp(realm, rid);
}

export function stateIo(realm: string, rid = RID): string {
  return gen.armStateIo(realm, rid);
}

export function stateStatus(realm: string, rid = RID): string {
  return gen.armStateStatus(realm, rid);
}

export function cmdSetDo(realm: string, rid = RID): string {
  return gen.armCmdSetDo(realm, rid);
}

export function cmdStop(realm: string, rid = RID): string {
  return gen.armCmdStop(realm, rid);
}

export function cmdClearProtectiveStop(realm: string, rid = RID): string {
  return gen.armCmdClearProtectiveStop(realm, rid);
}

export function cmdSetTcp(realm: string, rid = RID): string {
  return gen.armCmdSetTcp(realm, rid);
}

export function cmdJog(realm: string, rid = RID): string {
  return gen.armCmdJog(realm, rid);
}

export function actionPrefix(realm: string, rid = RID): string {
  return gen.armActionPrefix(realm, rid);
}

export function alive(realm: string, rid = RID): string {
  return gen.armAlive(realm, rid);
}

// ── dio ──────────────────────────────────────────────────────────────────

export function dioStateChannels(realm: string, rid: string): string {
  return gen.dioStateChannels(realm, rid);
}

export function dioCmdSet(realm: string, rid: string): string {
  return gen.dioCmdSet(realm, rid);
}

export function dioCmdForce(realm: string, rid: string): string {
  return gen.dioCmdForce(realm, rid);
}

export function dioAlive(realm: string, rid: string): string {
  return gen.dioAlive(realm, rid);
}

// ── program (one PackML unit per cell) ───────────────────────────────────

export const UNIT_COMMANDS = [
  "start", "hold", "unhold", "suspend", "unsuspend", "stop", "abort", "clear", "reset", "unload",
] as const;
export type UnitCommand = (typeof UNIT_COMMANDS)[number];

export function programsCatalog(realm: string): string {
  return gen.programCatalog(realm);
}

export function programsCmdLoad(realm: string): string {
  return gen.programCmdLoad(realm);
}

export function programsCmdSource(realm: string): string {
  return gen.programCmdSource(realm);
}

export function programsCmdSave(realm: string): string {
  return gen.programCmdSave(realm);
}

export function programsCmdDelete(realm: string): string {
  return gen.programCmdDelete(realm);
}

export function programLog(realm: string): string {
  return gen.programLog(realm);
}

export function programState(realm: string): string {
  return gen.programState(realm);
}

export function programCmd(realm: string, command: UnitCommand): string {
  return gen.programCmd(realm, command);
}

export function programCmdEvent(realm: string): string {
  return gen.programCmdEvent(realm);
}

export function programTransitions(realm: string): string {
  return gen.programTransitions(realm);
}

export function programAlive(realm: string): string {
  return gen.programAlive(realm);
}

// ── tags ─────────────────────────────────────────────────────────────────

export function tagsState(realm: string, rid: string): string {
  return gen.tagsStateTags(realm, rid);
}

export function tagsCmdWrite(realm: string, rid: string): string {
  return gen.tagsCmdWrite(realm, rid);
}

export function tagsCmdForce(realm: string, rid: string): string {
  return gen.tagsCmdForce(realm, rid);
}

export function tagsAlive(realm: string, rid: string): string {
  return gen.tagsAlive(realm, rid);
}

// ── washer ───────────────────────────────────────────────────────────────

export function washerState(realm: string, rid: string): string {
  return gen.washerStateStatus(realm, rid);
}

export function washerActionPrefix(realm: string, rid: string): string {
  return gen.washerActionPrefix(realm, rid);
}

export function washerCmdStopDoor(realm: string, rid: string): string {
  return gen.washerCmdStopDoor(realm, rid);
}

export function washerCmdGetRecipe(realm: string, rid: string): string {
  return gen.washerCmdGetRecipe(realm, rid);
}

export function washerCmdSetRecipe(realm: string, rid: string): string {
  return gen.washerCmdSetRecipe(realm, rid);
}

export function washerAlive(realm: string, rid: string): string {
  return gen.washerAlive(realm, rid);
}

// ── control (the one cell lease) ─────────────────────────────────────────

export function controlCmdAcquire(realm: string): string {
  return gen.controlCmdAcquire(realm);
}

export function controlCmdRelease(realm: string): string {
  return gen.controlCmdRelease(realm);
}

export function controlStateOwner(realm: string): string {
  return gen.controlStateOwner(realm);
}

export function controlAlive(realm: string): string {
  return gen.controlAlive(realm);
}

// ── config store (realm-less) ────────────────────────────────────────────

export function configFramesGlob(): string {
  return gen.configFramesGlob();
}

export function configFrame(name: string): string {
  return gen.configFrame(name);
}

export function configSceneGlob(): string {
  return gen.configSceneGlob();
}

export function configScene(name: string): string {
  return gen.configScene(name);
}

/** Map an `asset://wf/<rel>` mesh uri to its served public URL. The shared
 *  scene GLBs are copied into web/public/assets by sync-assets.mjs, so
 *  `asset://wf/foo.glb` is fetched at `/assets/foo.glb`. A non-asset uri is
 *  returned unchanged. */
export function assetUrl(uri: string): string {
  const prefix = "asset://wf/";
  return uri.startsWith(prefix) ? "/assets/" + uri.slice(prefix.length) : uri;
}

export function configIntrinsicsGlob(): string {
  return gen.configIntrinsicsGlob();
}

export function configIntrinsics(cid = CID): string {
  return gen.configIntrinsics(cid);
}

export function configPosesGlob(): string {
  return gen.configPosesGlob();
}

export function configProgramPosesGlob(program: string): string {
  return gen.configProgramPosesGlob(program);
}

export function configProgramPose(program: string, name: string): string {
  return gen.configProgramPose(program, name);
}

/** Hand-placed node positions of a program's graph view: {positions: {state: [x, y]}}. */
export function configProgramLayout(program: string): string {
  return gen.configProgramLayout(program);
}

export function configPose(name: string): string {
  return gen.configPose(name);
}

export function configTcpsGlob(rid = RID): string {
  return gen.configTcpsGlob(rid);
}

export function configTcp(name: string, rid = RID): string {
  return gen.configTcp(rid, name);
}

export function configCmdSet(): string {
  return gen.configCmdSet();
}

export function configCmdDelete(): string {
  return gen.configCmdDelete();
}

// ── camera2d ─────────────────────────────────────────────────────────────

export const CID = "cam0";

export function camImage(realm: string, cid = CID): string {
  return gen.camera2dImage(realm, cid);
}

export function camStatus(realm: string, cid = CID): string {
  return gen.camera2dStateStatus(realm, cid);
}

export function camAlive(realm: string, cid = CID): string {
  return gen.camera2dAlive(realm, cid);
}

/** actions: grab | configure | stream_start | stream_stop */
export function camCmd(realm: string, action: string, cid = CID): string {
  return `${gen.camera2dPrefix(realm, cid)}/cmd/${action}`;
}

export function camProducerCmd(realm: string, action: "acquire" | "release", cid = CID): string {
  return action === "acquire"
    ? gen.camera2dProducerCmdAcquire(realm, cid)
    : gen.camera2dProducerCmdRelease(realm, cid);
}

export function camProducerOwner(realm: string, cid = CID): string {
  return gen.camera2dProducerStateOwner(realm, cid);
}

export function camProducerDemand(realm: string, cid = CID): string {
  return gen.camera2dProducerStateDemand(realm, cid);
}

export function camProducerIngress(realm: string, cid = CID): string {
  return gen.camera2dProducerIngress(realm, cid);
}

export function camProducerRender(realm: string, clientId: string, cid = CID): string {
  return gen.camera2dProducerRender(realm, cid, clientId);
}

// ── supervisor ───────────────────────────────────────────────────────────

export function supervisorAlive(realm: string, node = "main"): string {
  return gen.supervisorAlive(realm, node);
}

export function supervisorDescriptor(realm: string, node = "main"): string {
  return gen.supervisorDescriptor(realm, node);
}

export function supervisorDevices(realm: string, node = "main"): string {
  return gen.supervisorDevices(realm, node);
}

export function supervisorCmdSetSource(realm: string, node = "main"): string {
  return gen.supervisorCmdSetSource(realm, node);
}

/** All services' log streams of one supervisor node (subscribe or query). */
export function supervisorLogGlob(realm: string, node = "main"): string {
  return gen.supervisorLogGlob(realm, node);
}

export function supervisorEvents(realm: string, node = "main"): string {
  return gen.supervisorEvents(realm, node);
}

// ── audit (wf/core/audit.py) ─────────────────────────────────────────────

/** Every service's query/reply echo stream (see wf/core/audit.py). */
export function auditGlob(realm: string): string {
  return `${realm}/audit/*`;
}
