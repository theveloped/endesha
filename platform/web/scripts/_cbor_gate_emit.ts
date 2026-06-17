// CBOR wire round-trip gate (TS write side -> Python cbor2 decode + from_wire).
// Run: node --experimental-strip-types scripts/_cbor_gate_emit.ts
// Emits one .cbor file per message into scripts/_cbor_out/, plus a manifest the
// Python side checks. Verifies the TS encoder produces wire bytes Python decodes
// with correct TYPES (float vs int, bool, bytes, null-vs-absent pose).
import { mkdirSync, writeFileSync } from "node:fs";
import { encodeWire } from "../src/lib/camera2d/cbor.ts";
import {
  ackWire,
  cameraStatusWire,
  frameHeaderWire,
  grabReplyWire,
  streamParamsWire,
} from "../src/lib/camera2d/messages.ts";

const dir = "scripts/_cbor_out";
mkdirSync(dir, { recursive: true });

const cases: Record<string, Uint8Array> = {};

cases["ack"] = encodeWire(ackWire(true, null));
cases["ack_err"] = encodeWire(ackWire(false, "boom"));

// FrameHeader WITH pose (integral pose values to stress float-forcing).
cases["header_pose"] = encodeWire(
  frameHeaderWire({
    t_capture: 1_700_000_000_000_000_000,
    frame_id: "camera2d/cam0/optical",
    w: 800,
    h: 800,
    encoding: "jpeg",
    exposure_us: 10000.0,
    gain_db: 0.0, // integral float -> must decode as Python float
    seq: 7,
    clock_domain: "host",
    pose: { frame: "world", xyz: [0.5, 0, 0.45], quat: [1, 0, 0, 0] },
  }),
);
// FrameHeader WITHOUT pose -> 'pose' key must be ABSENT.
cases["header_nopose"] = encodeWire(
  frameHeaderWire({
    t_capture: 42,
    frame_id: "camera2d/cam0/optical",
    w: 200,
    h: 200,
    encoding: "jpeg",
    exposure_us: 20000.0,
    gain_db: 1.5,
    seq: 0,
    clock_domain: "host",
    pose: null,
  }),
);

cases["stream"] = encodeWire(
  streamParamsWire({ rate_hz: 15.0, scale: 0.25, roi: null, encoding: "jpeg", quality: 75 }),
);

cases["grab_ok"] = encodeWire(
  grabReplyWire(
    true,
    null,
    frameHeaderWire({
      t_capture: 99,
      frame_id: "camera2d/cam0/optical",
      w: 800,
      h: 800,
      encoding: "jpeg",
      exposure_us: 10000.0,
      gain_db: 0.0,
      seq: 1,
      clock_domain: "host",
      pose: null,
    }),
    new Uint8Array([0xff, 0xd8, 0xff, 0xe0, 1, 2, 3]), // JPEG-ish bytes
  ),
);
cases["grab_err"] = encodeWire(grabReplyWire(false, "camera is streaming", null, null));

cases["status_idle"] = encodeWire(
  cameraStatusWire({
    t: 1_700_000_000_000_000_001,
    connected: true,
    streaming: false,
    stream: null,
    exposure_us: 10000.0,
    gain_db: 0.0,
    achieved_rate_hz: 0.0, // integral float -> must decode float
    error: null,
  }),
);
cases["status_streaming"] = encodeWire(
  cameraStatusWire({
    t: 1_700_000_000_000_000_002,
    connected: true,
    streaming: true,
    stream: { rate_hz: 15.0, scale: 0.25, roi: [0, 0, 400, 400], encoding: "jpeg", quality: 75 },
    exposure_us: 10000.0,
    gain_db: 0.0,
    achieved_rate_hz: 14.9,
    error: null,
  }),
);

const manifest: string[] = [];
for (const [name, bytes] of Object.entries(cases)) {
  writeFileSync(`${dir}/${name}.cbor`, bytes);
  manifest.push(name);
}
writeFileSync(`${dir}/manifest.json`, JSON.stringify(manifest));
console.log(`emitted ${manifest.length} cbor cases to ${dir}`);
