// TS mirrors of the normative wire dicts in
// platform/packages/contracts/arm/src/wf/contracts/arm/messages.py
// (hand-written; codegen is a later design phase).
//
// Conventions: positions in meters, angles in radians, quaternions
// [qx, qy, qz, qw] (unit, Hamilton, scalar last), timestamps int
// nanoseconds. `t` is typed number | bigint: cbor-x may decode ns
// timestamps (> 2^53) as BigInt; they are display-only in this UI —
// render via Number(t).

export type WireTimestamp = number | bigint;

export interface JointState {
  t: WireTimestamp;
  q: number[];
  qd: number[];
  tau: number[];
  clock_domain: string;
}

export interface Pose {
  frame: string;
  xyz: number[];
  quat: number[];
}

export interface FlangeState {
  t: WireTimestamp;
  pose: Pose;
}

export interface TcpState {
  t: WireTimestamp;
  tcp_name: string;
  pose: Pose;
}

/** di/do are bit-packed with LSB = pin 0 (python attr `do_` -> wire `"do"`). */
export interface IoState {
  t: WireTimestamp;
  di: number;
  do: number;
  ai: number[];
  ao: number[];
}

// ── dio contract (wf/contracts/dio/messages.py) ─────────────────────────────

export type ChannelKind = "di" | "do" | "ai" | "ao";

export interface ChannelValue {
  kind: ChannelKind;
  value: boolean | number;
  forced: boolean;
  /** Provider address (bank/pin/index…) — the raw pin behind the name. */
  address?: Record<string, unknown>;
  /** True for a synthesized channel of an unmapped physical point (raw pin). */
  auto?: boolean;
}

export interface ChannelsState {
  t: WireTimestamp;
  channels: Record<string, ChannelValue>;
}

/** One entry of a dio device's cell ``config.channels`` mapping. */
export interface ChannelDecl {
  kind: ChannelKind;
  unit?: string;
  scale?: number;
  offset?: number;
  [address: string]: unknown;
}

export interface ArmStatus {
  t: WireTimestamp;
  mode: string;
  servo_on: boolean;
  estop: boolean;
  protective_stop: boolean;
  speed_scale: number;
  active_tcp: string;
  error: string | null;
  state_rate_hz: number;
}

export type DoBank = "standard" | "tool";

export interface SetDo {
  bank: DoBank;
  pin: number;
  value: boolean;
}

export interface Ack {
  ok: boolean;
  error: string | null;
}

/**
 * One free / ranged goal DOF (wf/contracts/arm/messages.py::Freedom).
 * `dof`: x|y|z (translation, m) or roll|pitch|yaw (rotation, rad). `frame`:
 * "reference" (pose's frame axes) | "tool" (TCP-local axes). A rotation may
 * omit min/max for a full [-pi,pi) sweep; a translation requires both.
 */
export interface Freedom {
  dof: "x" | "y" | "z" | "roll" | "pitch" | "yaw";
  frame?: "reference" | "tool";
  min?: number;
  max?: number;
  step?: number;
}

/**
 * Target is exactly one of {q: [6 floats]} | {pose: Pose}. A pose target is
 * resolved (frame lookup + IK) at goal acceptance. On a `movej` it is reached
 * by joint interpolation; on a `movel` the TCP travels a straight Cartesian
 * line. A pose target on the last waypoint may carry a `free` block: on movej
 * that is a loose END goal (one DOF free), on movel a path-loose move (one DOF
 * free along the whole path).
 */
export interface Waypoint {
  type: "movej" | "movel";
  target: { q: number[] } | { pose: Pose; free?: Freedom };
  speed: number | null;
  accel: number | null;
  blend_radius: number;
}

export interface ExecutePathGoal {
  waypoints: Waypoint[];
  client_id?: string | null;
}

// Hold-to-jog + control lease (wf/contracts/arm/messages.py).

export interface JogCommand {
  client_id: string;
  mode: "joint" | "cartesian";
  /** reference-frame NAME: "base" | "tool" | a config-frame name. */
  frame: string;
  /** len 6: joint -> rad/s per joint; cartesian -> [vx,vy,vz,wx,wy,wz]. */
  velocity: number[];
  t: WireTimestamp;
}

export interface ControlOwner {
  client_id: string;
  user: string;
  granted_at: WireTimestamp;
  expires_at: WireTimestamp;
}

export interface ControlOwnerState {
  t: WireTimestamp;
  owner: ControlOwner | null;
}

export interface AcquireControl {
  client_id: string;
  user: string;
}

export interface ControlAck {
  ok: boolean;
  owner: ControlOwner | null;
  error: string | null;
}

// Config store value shapes (wf/services/config/store.py). Served values
// are flat: the stored payload merged with service-stamped revision/t.

export interface FrameDef {
  parent: string;
  xyz: number[];
  quat: number[];
  source?: string;
  meta?: Record<string, unknown>;
  revision?: number;
  t?: WireTimestamp;
}

export interface PoseDef {
  q: number[];
  meta?: Record<string, unknown>;
  revision?: number;
}

export interface TcpDef {
  xyz: number[];
  quat: number[];
  role: string;
  selectable_as_tcp: boolean;
  revision?: number;
}

/** Scene geometry: a primitive (box/cylinder/sphere) or a shared mesh.
 *  Mirrors wf.core.scene `_GEOMETRY_TYPES`. */
export interface SceneGeometry {
  type: "box" | "cylinder" | "sphere" | "mesh";
  uri?: string;
  size?: number[];
  radius?: number;
  length?: number;
}

/** A `config/scene/{name}` object: geometry posed in a named frame. Served flat
 *  like the other config docs (wf/services/config/store.py). */
export interface SceneObject {
  frame: string;
  pose: { xyz: number[]; quat: number[] };
  geometry: SceneGeometry;
  meta?: Record<string, unknown>;
  revision?: number;
  t?: WireTimestamp;
}

// Action wire protocol (wf/core/action.py, design Appendix A).

// Mirrors wf.core.action.GoalState / TERMINAL_STATES exactly.
export type GoalStateWire =
  | "accepted"
  | "rejected"
  | "running"
  | "canceling"
  | "canceled"
  | "succeeded"
  | "failed"
  | "aborted";

export const TERMINAL_STATES: Record<string, true> = {
  rejected: true,
  canceled: true,
  succeeded: true,
  failed: true,
  aborted: true,
};

export function isTerminal(state: string): boolean {
  return TERMINAL_STATES[state] === true;
}

export interface GoalReply {
  goal_id: string;
  accepted: boolean;
  reason: string | null;
  state: GoalStateWire;
}

export interface GoalFeedback {
  t: WireTimestamp;
  goal_id: string;
  state: GoalStateWire;
  progress: number;
  data: { current_wp?: number };
}

export interface GoalResult {
  t: WireTimestamp;
  goal_id: string;
  state: GoalStateWire;
  ok: boolean;
  error: string | null;
  data: Record<string, unknown>;
}

export interface CancelReply {
  goal_id: string;
  state: GoalStateWire;
}

// Replay control plane (wf/services/recording/replayer.py).

export interface ReplayClock {
  t: WireTimestamp;
  t_data: WireTimestamp;
  rate: number;
  playing: boolean;
}

export interface ReplayStatus {
  ok: boolean;
  error: string | null;
  t_data: WireTimestamp;
  rate: number;
  playing: boolean;
}

export interface ReplayMark {
  t: WireTimestamp;
  label: string;
}

export interface ReplayInfo extends ReplayStatus {
  start_ns: WireTimestamp;
  end_ns: WireTimestamp;
  source_realm: string;
  marks: ReplayMark[];
}

/** cbor-x decodes uint64 < 2^53 as number, larger as BigInt — normalize before math. */
export function asBigInt(v: WireTimestamp): bigint {
  return typeof v === "bigint" ? v : BigInt(Math.trunc(v));
}

// camera2d contract (wf/contracts/camera2d/messages.py). Frame payloads
// are image bytes with this header CBOR-encoded in the sample ATTACHMENT.

export interface FrameHeader {
  t_capture: WireTimestamp;
  frame_id: string;
  w: number;
  h: number;
  encoding: string;
  exposure_us: number;
  gain_db: number;
  seq: number;
  clock_domain: string;
  // World<-optical camera pose at capture, when the producer knew it
  // (eye-in-hand cameras with a flange sample). Absent otherwise.
  pose?: Pose;
}

// camera intrinsics config doc (config/intrinsics/{cid}); served flat with
// the store's revision/t stamped on.
export interface Intrinsics {
  fx: number;
  fy: number;
  cx: number;
  cy: number;
  w: number;
  h: number;
  revision?: number;
  t?: WireTimestamp;
}

export interface StreamParams {
  rate_hz: number;
  scale: number;
  roi: number[] | null;
  encoding: string;
  quality: number;
}

export interface CameraStatus {
  t: WireTimestamp;
  connected: boolean;
  streaming: boolean;
  stream: StreamParams | null;
  exposure_us: number | null;
  gain_db: number | null;
  achieved_rate_hz: number;
  error: string | null;
}

/** cbor-x decodes CBOR byte strings to Uint8Array. */
export interface GrabReply {
  ok: boolean;
  error: string | null;
  header: FrameHeader | null;
  data: Uint8Array | null;
}


export interface SupervisorService {
  kind: string;
  instance_id: string;
  alive: boolean;
}

export interface SupervisorDescriptor {
  t: WireTimestamp;
  node: string;
  is_master: boolean;
  owns_resources: string[];
  always_on: SupervisorService[];
  started_at: WireTimestamp;
}

// Device inventory (supervisor/devices): the cell's logical devices, their
// available source modes, and the active mode per device (drives the UI tree).

export interface DeviceSource {
  mode: string; // live | sim | replay (declared)
  kind: string;
  launch: string; // "module" | "external"
}

export interface DeviceEntry {
  id: string;
  contract: string;
  model: string | null;
  active: string | null; // active mode, or null/off
  config?: Record<string, unknown>;
  sources: DeviceSource[];
  /** Set when another resource's provider process serves this device (e.g. the
   *  arm's IO bank as a dio device): follows the host's source, not switchable. */
  provided_by?: string;
}

export interface DevicesList {
  t: WireTimestamp;
  node: string;
  devices: DeviceEntry[];
}

export interface ProducerGrant {
  client_id: string;
  user: string;
  authority_id: string;
  epoch: number;
  granted_at: WireTimestamp;
  expires_at: WireTimestamp;
}

export interface ProducerOwnerState {
  t: WireTimestamp;
  owner: ProducerGrant | null;
}

export interface ProducerAck {
  ok: boolean;
  owner: ProducerGrant | null;
  error: string | null;
}

export interface ProducerDemand {
  t: WireTimestamp;
  stream: {
    rate_hz: number;
    scale: number;
    roi: number[] | null;
    encoding: string;
    quality: number;
  } | null;
  intrinsics: { w: number; h: number; fx: number; fy: number };
  mount_xyz: number[];
  mount_rpy_deg: number[];
  exposure_us: number;
  gain_db: number;
}

/** supervisor/cmd/set_source reply: `{ok, device_id?, source?, error?}`. */
export interface SetSourceReply {
  ok: boolean;
  device_id?: string;
  source?: string;
  error?: string;
}
