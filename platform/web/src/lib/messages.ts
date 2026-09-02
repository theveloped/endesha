import type { WireError } from "./envelope";

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

// ── program contract (wf/contracts/program/messages.py) ─────────────────────

export type UnitState =
  | "idle" | "starting" | "execute" | "completing" | "complete"
  | "holding" | "held" | "unholding" | "suspending" | "suspended" | "unsuspending"
  | "stopping" | "stopped" | "aborting" | "aborted" | "clearing" | "resetting";

/** A catalog entry's graph is `{}` (no states) when the module does not
 * import; only a graph with a non-empty states array is drawable. */
export function drawableGraph(graph: ProgramGraph | undefined): ProgramGraph | undefined {
  return graph !== undefined && Array.isArray(graph.states) && graph.states.length > 0 ? graph : undefined;
}

// ── program graph (wf/program/graph.py): the state machine as data ──────────

export interface GraphState {
  id: string;
  initial: boolean;
  final: boolean;
  parent: string | null;
  kind: "atomic" | "compound" | "parallel" | string;
}

export interface GraphTransition {
  id: string;
  source: string;
  target: string;
  event: string | null;
  cond: string[];
  unless: string[];
  internal: boolean;
}

export interface GraphTrigger {
  kind: "channel" | "timer" | string;
  event: string;
  params: Record<string, unknown>;
}

export interface GraphSource {
  class: number | null;
  states: Record<string, number>;
  transitions: Record<string, number>; // event -> line
  actions: Record<string, number>; // state -> line of run_<state>
  guards: Record<string, number>;
  hooks: Record<string, number>;
}

export interface ProgramGraph {
  states: GraphState[];
  transitions: GraphTransition[];
  triggers: GraphTrigger[];
  source?: GraphSource;
}

export interface CatalogEntry {
  name: string;
  roles: Record<string, string>; // role -> contract
  params: Record<string, unknown>;
  doc: string;
  path: string;
  error: string | null;
  hmi?: Record<string, string>; // event -> operator button label
  graph?: ProgramGraph;
}

export interface ProgramCatalog {
  t: WireTimestamp;
  programs: CatalogEntry[];
}

/** What would move the program on from an active state (debug aid). */
export interface WaitingFor {
  kind: "channel" | "timer" | "event";
  event: string;
  target?: string;
  role?: string;
  channel?: string;
  edge?: string;
  state?: string;
  seconds?: number;
}

export interface ProgramState {
  t: WireTimestamp;
  unit: UnitState;
  program: string | null;
  program_states: string[];
  actions: string[];
  reason: string | null;
  params: Record<string, unknown>;
  bindings: Record<string, string>;
  client_id: string | null;
  cycle: number;
  waiting_for?: WaitingFor[];
}

export interface ProgramLogLine {
  t: WireTimestamp;
  level: "info" | "warning" | "error";
  source: string;
  message: string;
}

/** One captured stdout/stderr line of a supervised child
 * (`{realm}/supervisor/{node}/log/{service}`). */
export interface ServiceLogLine {
  t: WireTimestamp;
  level: "debug" | "info" | "warning" | "error";
  stream: "stdout" | "stderr";
  source: string; // service name, e.g. hal.r1, program_runner
  message: string;
}

/** Supervisor lifecycle event (`{realm}/supervisor/{node}/events`). */
export interface SupervisorEvent {
  t: WireTimestamp;
  kind: string; // service_started | service_exited | service_stopped | spawn_failed | source_switched | supervisor_started
  service: string | null;
  exit_code?: number | null;
  device_id?: string;
  source?: string;
  provider?: string;
  error?: string;
  ok?: boolean;
  cell?: string;
}

/** Query/reply audit echo (`{realm}/audit/{service}`). */
export interface AuditRecord {
  t: WireTimestamp;
  service: string;
  key: string;
  params: string | null;
  request: unknown;
  reply: unknown;
  ok: boolean | null;
  error: string | null;
  duration_ms: number;
}

/** programs/cmd/source envelope value. */
export interface ProgramSourceReply {
  name: string;
  path: string;
  text: string;
}

/** programs/cmd/save envelope value (an import error rides in the entry). */
export interface ProgramSaveReply {
  entry: CatalogEntry;
}

export interface TransitionEvent {
  t: WireTimestamp;
  scope: "unit" | "program";
  source: string | null;
  target: string;
  event: string | null;
  detail: string | null;
}

// ── tags contract (wf/contracts/tags/messages.py) ───────────────────────────

export type TagType = "bool" | "int" | "float" | "string";

export interface TagValue {
  type: TagType;
  value: boolean | number | string;
  access: "r" | "rw";
  forced: boolean;
  address?: Record<string, unknown>;
  auto?: boolean;
}

export interface TagsState {
  t: WireTimestamp;
  tags: Record<string, TagValue>;
}

// ── washer contract (wf/contracts/washer/messages.py) ───────────────────────

export type WasherPhase =
  | "initializing"
  | "ready_to_load"
  | "door_open"
  | "door_moving"
  | "washing"
  | "ready_to_unload"
  | "fault";

export interface WasherStatus {
  t: WireTimestamp;
  phase: WasherPhase;
  door: "open" | "closed" | "moving" | "unknown";
  connected: boolean;
  auto: boolean;
  fault: boolean;
  fault_code: number;
  washing: boolean;
  ready_to_load: boolean;
  ready_to_unload: boolean;
  program: string;
  program_no: number;
  sequence: string | null;
  detail: string;
}

export interface RecipeStep {
  cleaning: number;
  time_s: number;
  movement: number;
  additional: number;
  pump_off: boolean;
}

export interface Recipe {
  name: string;
  steps: RecipeStep[];
  params: Record<string, number>;
}

export interface ParamSpec {
  title: string;
  min?: number;
  max?: number;
  choices?: number[];
  unit?: string;
}

export interface RecipeSchema {
  steps: number;
  step_fields: Record<string, ParamSpec>;
  params: Record<string, ParamSpec>;
}

/** cmd/get_recipe envelope value. */
export interface RecipeReply {
  recipe: Recipe;
  schema?: RecipeSchema;
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

// Config store value shapes (wf/services/config/store.py). Served values
// are flat: the stored payload merged with service-stamped revision/t.

export interface FrameDef {
  parent: string;
  xyz: number[]; // EFFECTIVE pose (calibrated when a calibration exists)
  quat: number[];
  source?: string; // "manual" | "calibration" | ...
  meta?: Record<string, unknown>;
  revision?: number;
  t?: WireTimestamp;
  /** Design value; set by the store on every manual write, kept by calibration writes. */
  nominal?: { xyz: number[]; quat: number[] };
  /** Present iff the effective pose came from a calibration. */
  calibration?: { t?: WireTimestamp; method?: string; residual?: number; by?: string; [k: string]: unknown };
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

export interface GoalFeedback {
  t: WireTimestamp;
  seq: number;
  goal_id: string;
  state: GoalStateWire;
  progress: number;
  detail: { current_wp?: number };
}

/** Parsed terminal outcome of a goal (the retained result envelope). */
export interface GoalResult {
  ok: boolean;
  value: Record<string, unknown>;
  error: WireError | null;
}

/** cancel envelope value. */
export interface CancelReply {
  state: GoalStateWire | "unknown_goal";
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

// Pinhole view used by the renderers (derived from CameraInfo).
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

// config/intrinsics/{cid} in the ROS sensor_msgs/CameraInfo layout
// (wf/core/camera_info.py); served flat with the store's revision/t stamped on.
export interface CameraInfo {
  width: number;
  height: number;
  distortion_model: string;
  D: number[];
  K: number[]; // 3x3 row-major: [fx,0,cx, 0,fy,cy, 0,0,1]
  R?: number[];
  P?: number[];
  revision?: number;
  t?: WireTimestamp;
}

/** Pinhole view of a CameraInfo doc (also accepts the legacy flat shape). */
export function intrinsicsFromCameraInfo(doc: CameraInfo | Intrinsics): Intrinsics {
  if ("K" in doc && Array.isArray(doc.K)) {
    return {
      fx: doc.K[0], fy: doc.K[4], cx: doc.K[2], cy: doc.K[5],
      w: doc.width, h: doc.height, revision: doc.revision, t: doc.t,
    };
  }
  return doc as Intrinsics;
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

/** supervisor/cmd/set_source envelope value. */
export interface SetSourceReply {
  device_id: string;
  source: string;
}
