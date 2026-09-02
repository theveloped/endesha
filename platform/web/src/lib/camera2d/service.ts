// Camera2dService — the camera2d contract served over zenoh-ts. A faithful TS
// port of the Python SimCameraDriver (platform/packages/hal/camera2d_sim/
// src/wf/hal/camera2d_sim/__main__.py): liveliness token, the four cmd/*
// queryables, the single `image` topic (JPEG payload + CBOR FrameHeader
// attachment), and a 1 Hz state/status — with a shared monotonic seq/t_capture
// across stream and grab, and grab REJECTED while streaming.
//
// Framework-agnostic: rendering is injected as `renderFrame(spec)`. The page
// (CameraHalPage) wires a Three.js renderer to it; unit tests pass a stub.
// The page is single-threaded, but the stream tick and a grab query can
// interleave across `await`s, so a 1-slot async mutex serialises render+publish
// (mirrors the Python `_gl_lock` / `_state_lock`).
import type { Query, Session } from "@eclipse-zenoh/zenoh-ts";
import {
  declareLivelinessToken,
  declareQueryable,
  declareRawPublisher,
  queryPayload,
  replyBytes,
  type RawPublisher,
  type Unsubscribe,
} from "../bus";
import { camAlive, camCmd, camImage, camStatus } from "../config";
import type { CameraStatus, Pose, StreamParams } from "../messages";
import { encodeWire } from "./cbor";
import {
  cameraStatusWire,
  ENCODING_JPEG,
  failWire,
  type FrameSpec,
  frameHeaderWire,
  grabValueWire,
  okWire,
  opticalFrame,
  parseConfigureCmd,
  parseFrameSpec,
  parseRequest,
  parseStreamParams,
  streamParamsWire,
  type WireMap,
} from "./messages";

/** One rendered frame: encoded JPEG bytes, its output dimensions, and the
 *  world<-optical pose actually used (null when no flange sample -> fallback,
 *  but the renderer still returns the fallback pose so the header stamps it). */
export interface RenderedFrame {
  jpeg: Uint8Array;
  w: number;
  h: number;
  pose: Pose | null;
}

/** Inputs the page injects: render a frame for a spec, and the synthetic
 *  exposure/gain reported in headers + status (virtual, like the Python HAL). */
export interface RenderFrame {
  (spec: FrameSpec): Promise<RenderedFrame>;
}

export interface Camera2dServiceOptions {
  session: Session;
  realm: string;
  cid: string;
  frameId: string;
  renderFrame: RenderFrame;
  /** Resource defaults merged into stream/grab specs (cell.yaml grab_defaults /
   *  stream_defaults + exposure_us/gain_db from the render block). */
  streamDefaults: Partial<StreamParams>;
  grabDefaults: Partial<FrameSpec>;
  exposureUs: number;
  gainDb: number;
}


export class Camera2dService {
  private readonly session: Session;
  private readonly realm: string;
  private readonly cid: string;
  private readonly frameId: string;
  private readonly renderFrame: RenderFrame;
  private readonly streamDefaults: Partial<StreamParams>;
  private readonly grabDefaults: Partial<FrameSpec>;

  private exposureUs: number;
  private gainDb: number;

  private seq = 0;
  private lastTCapture = 0n;
  private publishedCount = 0;
  private error: string | null = null;

  private streamParams: StreamParams | null = null;
  private streamTimer: ReturnType<typeof setTimeout> | null = null;

  private statusTimer: ReturnType<typeof setInterval> | null = null;
  private lastStatusCount = 0;
  private lastStatusT = 0;

  private imagePub: RawPublisher | null = null;
  private statusPub: RawPublisher | null = null;
  private readonly disposers: Unsubscribe[] = [];

  // 1-slot async mutex: render+publish never overlap (stream tick vs grab).
  private renderLock: Promise<void> = Promise.resolve();

  constructor(opts: Camera2dServiceOptions) {
    this.session = opts.session;
    this.realm = opts.realm;
    this.cid = opts.cid;
    this.frameId = opts.frameId;
    this.renderFrame = opts.renderFrame;
    this.streamDefaults = opts.streamDefaults;
    this.grabDefaults = opts.grabDefaults;
    this.exposureUs = opts.exposureUs;
    this.gainDb = opts.gainDb;
  }

  async start(): Promise<void> {
    this.imagePub = await declareRawPublisher(this.session, camImage(this.realm, this.cid), true);
    this.statusPub = await declareRawPublisher(this.session, camStatus(this.realm, this.cid), false);

    this.disposers.push(
      await declareQueryable(this.session, camCmd(this.realm, "grab", this.cid), (q) =>
        this.onGrab(q),
      ),
      await declareQueryable(this.session, camCmd(this.realm, "configure", this.cid), (q) =>
        this.onConfigure(q),
      ),
      await declareQueryable(this.session, camCmd(this.realm, "stream_start", this.cid), (q) =>
        this.onStreamStart(q),
      ),
      await declareQueryable(this.session, camCmd(this.realm, "stream_stop", this.cid), (q) =>
        this.onStreamStop(q),
      ),
    );
    // Liveliness token LAST: a watcher seeing `alive` can assume the queryables
    // and publishers are already declared.
    this.disposers.push(await declareLivelinessToken(this.session, camAlive(this.realm, this.cid)));

    this.lastStatusT = performance.now();
    this.statusTimer = setInterval(() => this.publishStatus(), 1000);
  }

  async stop(): Promise<void> {
    clearInterval(this.statusTimer ?? undefined);
    this.stopStream();
    for (const d of this.disposers.splice(0).reverse()) d();
    this.imagePub?.undeclare();
    this.statusPub?.undeclare();
  }

  // ── the one render+publish path (stream frames AND grabs) ────────────────

  /** Serialise a render+publish on the 1-slot mutex, return the FrameHeader
   *  wire dict (also published on the image topic). */
  private async renderAndPublish(spec: FrameSpec): Promise<{
    header: WireMap;
    data: Uint8Array;
    w: number;
    h: number;
  }> {
    const release = await this.acquire();
    try {
      const frame = await this.renderFrame(spec);
      const header = this.nextHeader(frame.w, frame.h, spec.encoding, frame.pose);
      this.imagePub?.put(frame.jpeg, encodeWire(header));
      this.publishedCount += 1;
      return { header, data: frame.jpeg, w: frame.w, h: frame.h };
    } finally {
      release();
    }
  }

  /** Build the next FrameHeader wire dict with monotonic seq + t_capture. */
  private nextHeader(
    w: number,
    h: number,
    encoding: string,
    pose: Pose | null,
  ): WireMap {
    // Synthetic exposure-midpoint on the host clock (ns), monotonic-forced.
    let tCapture = nowNs() - BigInt(Math.round(this.exposureUs * 500));
    if (tCapture <= this.lastTCapture) tCapture = this.lastTCapture + 1n;
    this.lastTCapture = tCapture;
    const seq = this.seq;
    this.seq += 1;
    return frameHeaderWire({
      t_capture: tCapture,
      frame_id: this.frameId,
      w,
      h,
      encoding,
      exposure_us: this.exposureUs,
      gain_db: this.gainDb,
      seq,
      clock_domain: "host",
      pose,
    });
  }

  // ── envelope boilerplate (mirrors wf.core.envelope.serve_query) ─────────
  private recentReplies = new Map<string, Uint8Array>();

  private async serveEnvelope(
    query: Query,
    op: (args: Record<string, unknown>) => Promise<WireMap>,
  ): Promise<void> {
    let reqId: string;
    let args: Record<string, unknown>;
    try {
      const parsed = parseRequest(queryPayload(query) as Record<string, unknown> | null);
      reqId = parsed.reqId;
      args = parsed.args;
    } catch (e) {
      await replyBytes(query, encodeWire(failWire("invalid", "bad_request", errMsg(e))));
      return;
    }
    let wire = this.recentReplies.get(reqId);
    if (wire === undefined) {
      wire = encodeWire(await op(args));
      this.recentReplies.set(reqId, wire);
      if (this.recentReplies.size > 256) {
        const oldest = this.recentReplies.keys().next().value;
        if (oldest !== undefined) this.recentReplies.delete(oldest);
      }
    }
    await replyBytes(query, wire);
  }

  // ── grab ─────────────────────────────────────────────────────────────────

  private async onGrab(query: Query): Promise<void> {
    await this.serveEnvelope(query, async (args) => {
      if (this.streamParams !== null) {
        return failWire("conflict", "streaming", "stop the stream first");
      }
      let spec: FrameSpec;
      try {
        spec = parseFrameSpec(args, this.grabDefaults);
      } catch (e) {
        return failWire("invalid", "bad_request", errMsg(e));
      }
      if (spec.encoding !== ENCODING_JPEG) {
        return failWire(
          "invalid",
          "unsupported_encoding",
          `encoding ${spec.encoding} not supported by sim renderer`,
        );
      }
      try {
        const { header, data } = await this.renderAndPublish(spec);
        return okWire(grabValueWire(header, data));
      } catch (e) {
        return failWire("internal", "grab_failed", errMsg(e));
      }
    });
  }

  // ── streaming ──────────────────────────────────────────────────────────

  private async onStreamStart(query: Query): Promise<void> {
    await this.serveEnvelope(query, async (args) => {
      let sp: StreamParams;
      try {
        sp = parseStreamParams(args, this.streamDefaults);
      } catch (e) {
        return failWire("invalid", "bad_request", errMsg(e));
      }
      if (sp.encoding !== ENCODING_JPEG) {
        return failWire(
          "invalid",
          "unsupported_encoding",
          `encoding ${sp.encoding} not supported by sim renderer`,
        );
      }
      this.stopStream(); // restart with new params if already streaming
      this.streamParams = sp;
      this.scheduleStreamTick(sp, performance.now());
      return okWire();
    });
  }

  private async onStreamStop(query: Query): Promise<void> {
    await this.serveEnvelope(query, async () => {
      this.stopStream(); // idempotent
      return okWire();
    });
  }

  private stopStream(): void {
    if (this.streamTimer !== null) {
      clearTimeout(this.streamTimer);
      this.streamTimer = null;
    }
    this.streamParams = null;
  }

  /** Paced stream loop via self-rescheduling setTimeout (drift-corrected),
   *  mirroring the Python monotonic-cadence `_stream_loop`. */
  private scheduleStreamTick(sp: StreamParams, nextDue: number): void {
    const period = 1000 / sp.rate_hz;
    const delay = Math.max(0, nextDue - performance.now());
    this.streamTimer = setTimeout(() => {
      void (async () => {
        if (this.streamParams !== sp) return; // stopped/replaced
        try {
          await this.renderAndPublish(sp);
        } catch (e) {
          this.error = `stream failed: ${errMsg(e)}`;
        }
        if (this.streamParams !== sp) return;
        let due = nextDue + period;
        if (due < performance.now()) due = performance.now() + period; // fell behind -> resync
        this.scheduleStreamTick(sp, due);
      })();
    }, delay);
  }

  // ── configure (virtual exposure/gain) ────────────────────────────────────

  private async onConfigure(query: Query): Promise<void> {
    await this.serveEnvelope(query, async (args) => {
      try {
        const cmd = parseConfigureCmd(args);
        if (cmd.exposure_us !== null) this.exposureUs = cmd.exposure_us;
        if (cmd.gain_db !== null) this.gainDb = cmd.gain_db;
        return okWire();
      } catch (e) {
        return failWire("invalid", "bad_request", errMsg(e));
      }
    });
  }

  // ── status (1 Hz) ────────────────────────────────────────────────────────

  private publishStatus(): void {
    const now = performance.now();
    const elapsed = (now - this.lastStatusT) / 1000;
    const rate = elapsed > 0 ? (this.publishedCount - this.lastStatusCount) / elapsed : 0;
    this.lastStatusCount = this.publishedCount;
    this.lastStatusT = now;
    const status: CameraStatus = {
      t: nowNs(),
      connected: true,
      streaming: this.streamParams !== null,
      stream: this.streamParams,
      exposure_us: this.exposureUs,
      gain_db: this.gainDb,
      achieved_rate_hz: rate,
      error: this.error,
    };
    this.statusPub?.put(encodeWire(cameraStatusWire(status)));
  }

  // ── 1-slot async mutex ───────────────────────────────────────────────────

  private async acquire(): Promise<() => void> {
    const prior = this.renderLock;
    const { promise, resolve } = Promise.withResolvers<void>();
    this.renderLock = prior.then(() => promise);
    await prior;
    return resolve;
  }
}

/** Host wall-clock nanoseconds as BigInt (matches wf.core.time.now_ns). */
function nowNs(): bigint {
  // Date.now() is ms; performance gives sub-ms but not an epoch. The contract
  // only needs strictly-increasing host-domain ns near wall time, so epoch ms
  // scaled to ns is sufficient (monotonic-forced in nextHeader anyway).
  return BigInt(Date.now()) * 1_000_000n;
}

function errMsg(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

// streamParamsWire/cameraStatusWire/opticalFrame are re-exported for the page +
// tests to build matching specs without reaching into ./messages internals.
export { opticalFrame, streamParamsWire };
