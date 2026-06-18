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
 * Target is exactly one of {q: [6 floats]} | {pose: Pose}. Pose targets are
 * movej-only and resolved (frame lookup + IK) at goal acceptance.
 */
export interface Waypoint {
  type: string;
  target: { q: number[] } | { pose: Pose };
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

// task contract (wf/contracts/task/keys.py + task_runner service). `state` is
// latest-wins (DROP); `result` is the terminal aggregate. `configuration` is
// the set of active statechart state ids — multiple entries while the two
// parallel regions (inspect + conveyor) are live.

export interface TaskTransition {
  event: string;
  source: string | null;
  target: string | null;
  t: WireTimestamp;
}

export interface TaskContext {
  by_pose?: { pose: string; detections: BarcodeDetection[] }[];
  conveyor?: ConveyorOutcome | null;
  summary?: TaskSummary | null;
}

export interface TaskState {
  t: WireTimestamp;
  flow: string;
  configuration: string[];
  terminated: boolean;
  history: TaskTransition[];
  context: TaskContext;
}

export interface BarcodeDetection {
  text: string;
  format: string;
  corners: number[][];
}

export interface ConveyorOutcome {
  tripped_by: "di" | "timeout";
  elapsed_s: number;
}

export interface TaskSummary {
  codes: string[];
  by_pose: { pose: string; detections: BarcodeDetection[] }[];
  conveyor: ConveyorOutcome | null;
}

export interface TaskResult {
  t: WireTimestamp;
  flow: string;
  ok: boolean;
  error: string | null;
  summary: TaskSummary | null;
}

/** cmd/start reply: `{ok:true, flow}` or `{ok:false, error}` (busy/unknown_pose:*). */
export interface TaskStartReply {
  ok: boolean;
  flow?: string;
  error?: string;
}

// supervisor contract (wf/contracts/supervisor/keys.py + supervisor service).
// The catalog is latest-wins: the selectable flows with their RESOLVED role
// bindings (role -> the resource id it bound to) and online state.

export interface FlowRoleBinding {
  contract: string;
  resource_id: string;
}

export interface FlowCatalogEntry {
  name: string;
  roles: Record<string, FlowRoleBinding>;
  pipeline: string | null;
  format: string | null;
  online: boolean;
  error: string | null;
}

export interface FlowsCatalog {
  t: WireTimestamp;
  realm: string;
  flows: FlowCatalogEntry[];
}

/** flows/cmd/start|stop reply: `{ok:true, flow}` or `{ok:false, error}`. */
export interface FlowCmdReply {
  ok: boolean;
  flow?: string;
  error?: string;
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
  sources: DeviceSource[];
}

export interface DevicesList {
  t: WireTimestamp;
  node: string;
  devices: DeviceEntry[];
}

/** supervisor/cmd/set_source reply: `{ok, device_id?, source?, error?}`. */
export interface SetSourceReply {
  ok: boolean;
  device_id?: string;
  source?: string;
  error?: string;
}
