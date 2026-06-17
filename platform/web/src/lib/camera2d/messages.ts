// Write-side wire builders for the camera2d contract, mirroring the to_wire
// methods in platform/packages/contracts/camera2d/src/wf/contracts/camera2d/
// messages.py. The READ-side interfaces (FrameHeader, StreamParams,
// CameraStatus, GrabReply, Pose) already live in lib/messages.ts; this module
// is the producer half the TS HAL needs.
//
// Float discipline: every field the Python dataclass declares `float` is
// wrapped with f()/farr() so it serializes as CBOR float64 even when its JS
// value is integral (1.0 === 1 in JS). Guaranteed-int fields (t_capture, w, h,
// seq, t, quality, roi) stay bare numbers. See cbor.ts for why.
//
// Key ORDER matches each Python to_wire emission order exactly (cbor2 keeps
// insertion order). The ONLY omitted-when-null key in the whole contract is
// FrameHeader.pose; every other nullable field is emitted as explicit null.

import { type Flt, type Wire, f, farr } from "./cbor";
import type { CameraStatus, Pose, StreamParams } from "../messages";

export type WireMap = { [k: string]: Wire };

export const ENCODING_JPEG = "jpeg";
export const ENCODING_BAYER_RG8 = "BayerRG8";
export const ENCODING_MONO8 = "Mono8";
export const ENCODINGS = [ENCODING_JPEG, ENCODING_BAYER_RG8, ENCODING_MONO8];

/** Realm-less optical frame name `camera2d/{cid}/optical` (keys.py). The
 *  FrameHeader.frame_id every camera frame carries. */
export function opticalFrame(cid: string): string {
  return `camera2d/${cid}/optical`;
}

// ── Ack ──────────────────────────────────────────────────────────────────
export interface Ack {
  ok: boolean;
  error: string | null;
}

export function ackWire(ok: boolean, error: string | null = null): WireMap {
  return { ok, error };
}

// ── FrameSpec / StreamParams (parsed from cmd payloads) ────────────────────
export interface FrameSpec {
  scale: number;
  roi: number[] | null;
  encoding: string;
  quality: number;
}

const FRAME_SPEC_DEFAULTS: FrameSpec = {
  scale: 1.0,
  roi: null,
  encoding: ENCODING_BAYER_RG8,
  quality: 95,
};

/** Parse + validate a cmd/grab FrameSpec from a decoded wire dict, merging the
 *  resource grab_defaults. Throws on invalid input (the error string is
 *  surfaced in the GrabReply, matching the Python __post_init__ messages). */
export function parseFrameSpec(
  d: Record<string, unknown>,
  defaults: Partial<FrameSpec> = {},
): FrameSpec {
  const m = { ...FRAME_SPEC_DEFAULTS, ...defaults, ...d };
  const scale = Number(m.scale);
  const quality = Number(m.quality);
  const encoding = String(m.encoding);
  const roi = m.roi == null ? null : (m.roi as number[]).map((v) => Math.trunc(Number(v)));
  if (!(scale > 0 && scale <= 1)) throw new Error(`scale must be in (0, 1], got ${scale}`);
  if (!ENCODINGS.includes(encoding)) {
    throw new Error(`encoding must be one of ${ENCODINGS.join(",")}, got '${encoding}'`);
  }
  if (!(quality >= 1 && quality <= 100)) {
    throw new Error(`quality must be in [1, 100], got ${quality}`);
  }
  if (roi !== null) {
    if (roi.length !== 4) throw new Error(`roi must be [x, y, w, h], got ${JSON.stringify(roi)}`);
    const [x, y, w, h] = roi;
    if (x < 0 || y < 0) throw new Error(`roi x/y must be non-negative, got ${JSON.stringify(roi)}`);
    if (w <= 0 || h <= 0) throw new Error(`roi w/h must be positive, got ${JSON.stringify(roi)}`);
  }
  if (encoding === ENCODING_BAYER_RG8 && scale !== 1.0) {
    throw new Error("scale requires jpeg encoding");
  }
  return { scale, roi, encoding, quality };
}

/** Parse + validate a cmd/stream_start StreamParams (FrameSpec + rate_hz). */
export function parseStreamParams(
  d: Record<string, unknown>,
  defaults: Partial<StreamParams> = {},
): StreamParams {
  const spec = parseFrameSpec(d, defaults);
  const rate_hz = Number(d.rate_hz ?? defaults.rate_hz ?? 15.0);
  if (!(rate_hz > 0 && rate_hz <= 60)) {
    throw new Error(`rate_hz must be in (0, 60], got ${rate_hz}`);
  }
  return { ...spec, rate_hz };
}

/** StreamParams wire is FLAT: {scale, roi, encoding, quality, rate_hz}. */
export function streamParamsWire(sp: StreamParams): WireMap {
  return {
    scale: f(sp.scale),
    roi: sp.roi === null ? null : sp.roi.map((v) => Math.trunc(v)),
    encoding: sp.encoding,
    quality: Math.trunc(sp.quality),
    rate_hz: f(sp.rate_hz),
  };
}

// ── ConfigureCmd (parsed from cmd/configure) ───────────────────────────────
export interface ConfigureCmd {
  exposure_us: number | null;
  gain_db: number | null;
  auto_exposure: boolean | null;
  auto_gain: boolean | null;
  auto_wb: boolean | null;
  wb_red: number | null;
  wb_blue: number | null;
}

export function parseConfigureCmd(d: Record<string, unknown>): ConfigureCmd {
  const num = (v: unknown): number | null => (v == null ? null : Number(v));
  const bool = (v: unknown): boolean | null => (v == null ? null : Boolean(v));
  return {
    exposure_us: num(d.exposure_us),
    gain_db: num(d.gain_db),
    auto_exposure: bool(d.auto_exposure),
    auto_gain: bool(d.auto_gain),
    auto_wb: bool(d.auto_wb),
    wb_red: num(d.wb_red),
    wb_blue: num(d.wb_blue),
  };
}

// ── pose ───────────────────────────────────────────────────────────────────
function poseWire(pose: Pose): WireMap {
  return { frame: pose.frame, xyz: farr(pose.xyz), quat: farr(pose.quat) };
}

// ── FrameHeader ────────────────────────────────────────────────────────────
export interface FrameHeaderInit {
  t_capture: number | bigint;
  frame_id: string;
  w: number;
  h: number;
  encoding: string;
  exposure_us: number;
  gain_db: number;
  seq: number;
  clock_domain: string;
  pose: Pose | null;
}

/** FrameHeader.to_wire: pose key APPENDED only when present (the one
 *  omitted-when-null field in the contract). */
export function frameHeaderWire(hdr: FrameHeaderInit): WireMap {
  const d: WireMap = {
    t_capture: hdr.t_capture,
    frame_id: hdr.frame_id,
    w: Math.trunc(hdr.w),
    h: Math.trunc(hdr.h),
    encoding: hdr.encoding,
    exposure_us: f(hdr.exposure_us),
    gain_db: f(hdr.gain_db),
    seq: Math.trunc(hdr.seq),
    clock_domain: hdr.clock_domain,
  };
  if (hdr.pose !== null) d.pose = poseWire(hdr.pose);
  return d;
}

// ── GrabReply ──────────────────────────────────────────────────────────────
export function grabReplyWire(
  ok: boolean,
  error: string | null,
  header: WireMap | null,
  data: Uint8Array | null,
): WireMap {
  return { ok, error, header, data };
}

// ── CameraStatus ───────────────────────────────────────────────────────────
export function cameraStatusWire(s: CameraStatus): WireMap {
  const flt = (v: number | null): Flt | null => (v === null ? null : f(v));
  return {
    t: s.t,
    connected: s.connected,
    streaming: s.streaming,
    stream: s.stream === null ? null : streamParamsWire(s.stream),
    exposure_us: flt(s.exposure_us),
    gain_db: flt(s.gain_db),
    achieved_rate_hz: f(s.achieved_rate_hz),
    error: s.error,
  };
}
