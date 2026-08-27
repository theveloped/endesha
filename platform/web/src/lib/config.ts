// Key space for the `arm` contract, mirroring wf/contracts/arm/keys.py.
// The realm is caller-supplied: every builder takes the full namespace prefix
// string ("cell" or "replay/{sid}") — the UI's switcher picks it and identical
// components render the live cell or a recording by prefix swap alone.

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
  return `replay/${sid}/cmd/${action}`;
}

export function replayClock(sid: string): string {
  return `replay/${sid}/clock`;
}

/** Matches replay/{sid}/{contract}/{rid}/alive liveliness tokens. */
export const REPLAY_ALIVE_GLOB = "replay/*/*/*/alive";

function prefix(realm: string, rid: string): string {
  return `${realm}/arm/${rid}`;
}

export function stateJoints(realm: string, rid = RID): string {
  return `${prefix(realm, rid)}/state/joints`;
}

export function stateFlange(realm: string, rid = RID): string {
  return `${prefix(realm, rid)}/state/flange`;
}

export function stateTcp(realm: string, rid = RID): string {
  return `${prefix(realm, rid)}/state/tcp`;
}

export function stateIo(realm: string, rid = RID): string {
  return `${prefix(realm, rid)}/state/io`;
}

export function stateStatus(realm: string, rid = RID): string {
  return `${prefix(realm, rid)}/state/status`;
}

export function cmdSetDo(realm: string, rid = RID): string {
  return `${prefix(realm, rid)}/cmd/set_do`;
}

export function cmdStop(realm: string, rid = RID): string {
  return `${prefix(realm, rid)}/cmd/stop`;
}

export function cmdClearProtectiveStop(realm: string, rid = RID): string {
  return `${prefix(realm, rid)}/cmd/clear_protective_stop`;
}

export function cmdSetTcp(realm: string, rid = RID): string {
  return `${prefix(realm, rid)}/cmd/set_tcp`;
}

export function cmdJog(realm: string, rid = RID): string {
  return `${prefix(realm, rid)}/cmd/jog`;
}

// dio contract (wf/contracts/dio/keys.py): named channels per dio device.
export function dioStateChannels(realm: string, rid: string): string {
  return `${realm}/dio/${rid}/state/channels`;
}

export function dioCmdSet(realm: string, rid: string): string {
  return `${realm}/dio/${rid}/cmd/set`;
}

export function dioCmdForce(realm: string, rid: string): string {
  return `${realm}/dio/${rid}/cmd/force`;
}

export function dioAlive(realm: string, rid: string): string {
  return `${realm}/dio/${rid}/alive`;
}

// program contract (wf/contracts/program/keys.py): one PackML unit per cell.
export const UNIT_COMMANDS = [
  "start", "hold", "unhold", "suspend", "unsuspend", "stop", "abort", "clear", "reset", "unload",
] as const;
export type UnitCommand = (typeof UNIT_COMMANDS)[number];

export function programsCatalog(realm: string): string {
  return `${realm}/programs/catalog`;
}

export function programsCmdLoad(realm: string): string {
  return `${realm}/programs/cmd/load`;
}

export function programsCmdSource(realm: string): string {
  return `${realm}/programs/cmd/source`;
}

export function programsCmdSave(realm: string): string {
  return `${realm}/programs/cmd/save`;
}

export function programsCmdDelete(realm: string): string {
  return `${realm}/programs/cmd/delete`;
}

export function programLog(realm: string): string {
  return `${realm}/program/log`;
}

export function programState(realm: string): string {
  return `${realm}/program/state`;
}

export function programCmd(realm: string, command: UnitCommand): string {
  return `${realm}/program/cmd/${command}`;
}

export function programCmdEvent(realm: string): string {
  return `${realm}/program/cmd/event`;
}

export function programTransitions(realm: string): string {
  return `${realm}/program/transitions`;
}

export function programAlive(realm: string): string {
  return `${realm}/program/alive`;
}

// tags contract (wf/contracts/tags/keys.py): named typed controller variables.
export function tagsState(realm: string, rid: string): string {
  return `${realm}/tags/${rid}/state/tags`;
}

export function tagsCmdWrite(realm: string, rid: string): string {
  return `${realm}/tags/${rid}/cmd/write`;
}

export function tagsCmdForce(realm: string, rid: string): string {
  return `${realm}/tags/${rid}/cmd/force`;
}

export function tagsAlive(realm: string, rid: string): string {
  return `${realm}/tags/${rid}/alive`;
}

// washer contract (wf/contracts/washer/keys.py): parts washer door/cycle/recipe.
export function washerState(realm: string, rid: string): string {
  return `${realm}/washer/${rid}/state/status`;
}

export function washerActionPrefix(realm: string, rid: string): string {
  return `${realm}/washer/${rid}/action`;
}

export function washerCmdStopDoor(realm: string, rid: string): string {
  return `${realm}/washer/${rid}/cmd/stop_door`;
}

export function washerCmdGetRecipe(realm: string, rid: string): string {
  return `${realm}/washer/${rid}/cmd/get_recipe`;
}

export function washerCmdSetRecipe(realm: string, rid: string): string {
  return `${realm}/washer/${rid}/cmd/set_recipe`;
}

export function washerAlive(realm: string, rid: string): string {
  return `${realm}/washer/${rid}/alive`;
}

// Cell-level control lease (wf/contracts/control/keys.py): ONE holder for every
// device in the cell, granted by the supervisor-hosted authority. No rid.
export function controlCmdAcquire(realm: string): string {
  return `${realm}/control/cmd/acquire`;
}

export function controlCmdRelease(realm: string): string {
  return `${realm}/control/cmd/release`;
}

export function controlStateOwner(realm: string): string {
  return `${realm}/control/state/owner`;
}

export function controlAlive(realm: string): string {
  return `${realm}/control/alive`;
}

export function actionPrefix(realm: string, rid = RID): string {
  return `${prefix(realm, rid)}/action`;
}

export function alive(realm: string, rid = RID): string {
  return `${prefix(realm, rid)}/alive`;
}

// Realm-less config store keys, mirroring wf/services/config/keys.py.
// Config is shared by all realms — no prefix swap.

export function configFramesGlob(): string {
  return "config/frames/**";
}

export function configFrame(name: string): string {
  return `config/frames/${name}`;
}

export function configSceneGlob(): string {
  return "config/scene/**";
}

export function configScene(name: string): string {
  return `config/scene/${name}`;
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
  return "config/intrinsics/**";
}

export function configIntrinsics(cid = CID): string {
  return `config/intrinsics/${cid}`;
}

export function configPosesGlob(): string {
  return "config/poses/**";
}

export function configProgramPosesGlob(program: string): string {
  return `config/programs/${program}/poses/**`;
}

export function configProgramPose(program: string, name: string): string {
  return `config/programs/${program}/poses/${name}`;
}

/** Hand-placed node positions of a program's graph view: {positions: {state: [x, y]}}. */
export function configProgramLayout(program: string): string {
  return `config/programs/${program}/layout`;
}

export function configPose(name: string): string {
  return `config/poses/${name}`;
}

export function configTcpsGlob(rid = RID): string {
  return `config/arm/${rid}/tcp/**`;
}

export function configTcp(name: string, rid = RID): string {
  return `config/arm/${rid}/tcp/${name}`;
}

export function configCmdSet(): string {
  return "config/cmd/set";
}

export function configCmdDelete(): string {
  return "config/cmd/delete";
}

// Key space for the `camera2d` contract, mirroring
// wf/contracts/camera2d/keys.py.

export const CID = "cam0";

function camPrefix(realm: string, cid: string): string {
  return `${realm}/camera2d/${cid}`;
}

export function camImage(realm: string, cid = CID): string {
  return `${camPrefix(realm, cid)}/image`;
}

export function camStatus(realm: string, cid = CID): string {
  return `${camPrefix(realm, cid)}/state/status`;
}

export function camAlive(realm: string, cid = CID): string {
  return `${camPrefix(realm, cid)}/alive`;
}

/** actions: grab | configure | stream_start | stream_stop */
export function camCmd(realm: string, action: string, cid = CID): string {
  return `${camPrefix(realm, cid)}/cmd/${action}`;
}

export function camProducerCmd(realm: string, action: "acquire" | "release", cid = CID): string {
  return `${camPrefix(realm, cid)}/producer/cmd/${action}`;
}

export function camProducerOwner(realm: string, cid = CID): string {
  return `${camPrefix(realm, cid)}/producer/state/owner`;
}

export function camProducerDemand(realm: string, cid = CID): string {
  return `${camPrefix(realm, cid)}/producer/state/demand`;
}

export function camProducerIngress(realm: string, cid = CID): string {
  return `${camPrefix(realm, cid)}/producer/ingress`;
}

export function camProducerRender(realm: string, clientId: string, cid = CID): string {
  return `${camPrefix(realm, cid)}/producer/clients/${clientId}/render`;
}

// Supervisor process and device-inventory key space.

export function supervisorAlive(realm: string, node = "main"): string {
  return `${realm}/supervisor/${node}/alive`;
}

export function supervisorDescriptor(realm: string, node = "main"): string {
  return `${realm}/supervisor/${node}/descriptor`;
}

export function supervisorDevices(realm: string, node = "main"): string {
  return `${realm}/supervisor/${node}/devices`;
}

export function supervisorCmdSetSource(realm: string, node = "main"): string {
  return `${realm}/supervisor/${node}/cmd/set_source`;
}

/** Captured stdout/stderr of every supervised child; each key is one service.
 * Subscribe live and query the same glob for the per-service ring buffers. */
export function supervisorLogGlob(realm: string, node = "main"): string {
  return `${realm}/supervisor/${node}/log/*`;
}

/** Supervisor lifecycle events (started/exited/stopped/source_switched/...);
 * queryable for the ring: `{events: [...]}`. */
export function supervisorEvents(realm: string, node = "main"): string {
  return `${realm}/supervisor/${node}/events`;
}

/** Query/reply audit echoes: one key per service (`{realm}/audit/<service>`). */
export function auditGlob(realm: string): string {
  return `${realm}/audit/*`;
}
