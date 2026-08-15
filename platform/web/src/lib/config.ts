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
