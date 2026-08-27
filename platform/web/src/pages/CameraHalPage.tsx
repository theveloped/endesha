// camera2d HAL page: the headless browser process IS the sim camera. It renders
// the shared twin scene (same Three.js renderer, so the camera image and the
// digital twin match by construction) from the eye-in-hand optical pose, and
// serves the FULL camera2d contract over zenoh-ts via Camera2dService — the
// liveliness token, the four cmd/* queryables, the `image` topic (JPEG payload +
// CBOR FrameHeader attachment), and 1 Hz state/status. No pyrender, no Puppeteer
// in the serving path.
//
// Renderer parity with the retired Python Renderer (render.py):
//   - pose: computed HERE from the arm state/flange + the flange->optical mount
//     (the page is the producer now; nothing else publishes the pose),
//   - intrinsics + mount + resolution: from the supervisor's shared cam0 device
//     config, with query parameters retained only as legacy fallbacks,
//   - lighting: full ambient + one directional sun (render.py _SUN_POSE),
//   - background: gray 90; scene composition is shared with the browser producer.
//
// Mounted by headless-main.tsx under headless.html; never in the twin's router.
import { useEffect, useMemo, useRef, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { SimCameraRenderer, type GrabFrame } from "../components/SimCameraRenderer";
import {
  connect,
  query,
  subscribeConfigList,
  subscribeLatest,
  type Unsubscribe,
} from "../lib/bus";
import { Camera2dService } from "../lib/camera2d/service";
import { opticalFrame } from "../lib/camera2d/messages";
import {
  DEFAULT_WS_URL,
  configFramesGlob,
  configSceneGlob,
  stateFlange,
  stateJoints,
  supervisorDevices,
} from "../lib/config";
import { BASE_FRAME, frameWorldMatrix } from "../lib/framemath";
import type {
  DevicesList,
  FlangeState,
  FrameDef,
  Intrinsics,
  JointState,
  SceneObject,
} from "../lib/messages";

const STREAM_RENDER_SCALE = 0.25;

function clampNum(raw: unknown, fallback: number, lo: number, hi: number): number {
  if (raw === null || raw === undefined) return fallback;
  const value = Number(raw);
  return Number.isFinite(value) ? Math.min(hi, Math.max(lo, value)) : fallback;
}

function vecParam(raw: unknown, fallback: number[]): number[] {
  const parts = Array.isArray(raw)
    ? raw.map(Number)
    : typeof raw === "string"
      ? raw.split(",").map(Number)
      : [];
  return parts.length === fallback.length && parts.every(Number.isFinite)
    ? parts
    : fallback;
}

function recordValue(raw: unknown): Record<string, unknown> {
  return raw !== null && typeof raw === "object" && !Array.isArray(raw)
    ? raw as Record<string, unknown>
    : {};
}

function delay(ms: number): Promise<void> {
  const { promise, resolve } = Promise.withResolvers<void>();
  setTimeout(resolve, ms);
  return promise;
}

export default function CameraHalPage() {
  const [session, setSession] = useState<Session | null>(null);
  const [frames, setFrames] = useState<{ name: string; def: FrameDef }[]>([]);
  const [scene, setScene] = useState<{ name: string; obj: SceneObject }[]>([]);

  const flangeRef = useRef<FlangeState | null>(null);
  const jointsRef = useRef<JointState | null>(null);
  const grabRef = useRef<GrabFrame | null>(null);
  const serviceRef = useRef<Camera2dService | null>(null);
  // This device's active source mode (from the supervisor's devices inventory).
  // The headless renderer serves the camera2d contract ONLY while it is `sim` —
  // when switched to live/replay/off it backs off so the supervisor-spawned
  // provider (genicam / replay_camera) or nothing owns the contract.
  const [isSimActive, setIsSimActive] = useState(false);
  const [deviceConfig, setDeviceConfig] = useState<Record<string, unknown> | null>(null);

  const params = new URLSearchParams(window.location.search);
  const wsUrl = params.get("ws") ?? DEFAULT_WS_URL;
  const realm = params.get("realm") ?? "cell";
  const cid = params.get("cid") ?? "cam0";

  // The logical device config is authoritative for optics shared by the
  // headless and in-tab simulated providers. Query params are legacy fallbacks
  // for standalone use before a supervisor inventory is available.
  const renderConfig = recordValue(deviceConfig?.render);
  const w = Math.round(
    clampNum(renderConfig.width, clampNum(params.get("w"), 1280, 1, 8192), 1, 8192),
  );
  const h = Math.round(
    clampNum(renderConfig.height, clampNum(params.get("h"), 800, 1, 8192), 1, 8192),
  );
  const fx = clampNum(renderConfig.fx, clampNum(params.get("fx"), 900, 1, 1e5), 1, 1e5);
  const fy = clampNum(renderConfig.fy, clampNum(params.get("fy"), 900, 1, 1e5), 1, 1e5);
  const mountXyz = vecParam(
    deviceConfig?.mount_xyz ?? renderConfig.mount_xyz ?? params.get("mount_xyz"),
    [0, 0, 0.05],
  );
  const mountRpyDeg = vecParam(
    deviceConfig?.mount_rpy_deg ?? renderConfig.mount_rpy_deg ?? params.get("mount_rpy_deg"),
    [0, 0, 0],
  );
  const exposureUs = clampNum(
    deviceConfig?.exposure_us ?? params.get("exposure_us"),
    10000,
    1,
    1e9,
  );
  const gainDb = clampNum(deviceConfig?.gain_db ?? params.get("gain_db"), 0, -100, 100);

  const intrinsics: Intrinsics = { fx, fy, cx: (w - 1) / 2, cy: (h - 1) / 2, w, h };

  // Robot base pose (Z-up world matrix) from the config frame tree. The flange
  // pose `arm_sim` publishes is arm-base-relative; this lifts the eye-in-hand
  // camera into true world so it matches the world-frame scene meshes.
  const baseMatrix = useMemo(() => {
    const map = new Map(frames.map((fr) => [fr.name, fr.def]));
    return frameWorldMatrix(map, BASE_FRAME);
  }, [frames]);

  // The drawing buffer is sized to the stream render scale.

  // Open the session once.
  useEffect(() => {
    let s: Session | null = null;
    void (async () => {
      try {
        s = await connect(wsUrl);
        setSession(s);
      } catch (e) {
        console.error("camera2d HAL: connect failed:", e);
      }
    })();
    return () => void s?.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Live frames + scene: seed via GET, then track config edits (the config
  // service publishes each cmd/set value and a tombstone on cmd/delete) so a UI
  // scene/frame change re-renders the sim camera without a reload. Intrinsics
  // still come from query params (the render block), NOT config/intrinsics.
  useEffect(() => {
    if (session === null) return;
    const unsubs: Unsubscribe[] = [];
    let disposed = false;
    void (async () => {
      const us = await Promise.all([
        subscribeConfigList(session, configFramesGlob(), "config/frames/", (items) =>
          setFrames(items.map((i) => ({ name: i.name, def: i.value as FrameDef }))),
        ),
        subscribeConfigList(session, configSceneGlob(), "config/scene/", (items) =>
          setScene(items.map((i) => ({ name: i.name, obj: i.value as SceneObject }))),
        ),
      ]);
      if (disposed) us.forEach((u) => u());
      else unsubs.push(...us);
    })();
    return () => {
      disposed = true;
      unsubs.forEach((u) => u());
    };
  }, [session]);

  // Flange + joints streams into refs (decoupled from render): the eye-in-hand
  // camera pose is derived from the flange, and the rendered URDF arm + gripper
  // are driven by the joints (the lens sees the gripper up close, and the arm
  // when it swings into view).
  useEffect(() => {
    if (session === null) return;
    const unsubs: Unsubscribe[] = [];
    let disposed = false;
    void (async () => {
      const us = await Promise.all([
        subscribeLatest(
          session,
          stateFlange(realm),
          (msg) => {
            flangeRef.current = msg as FlangeState;
          },
          1,
        ),
        subscribeLatest(
          session,
          stateJoints(realm),
          (msg) => {
            jointsRef.current = msg as JointState;
          },
          1,
        ),
      ]);
      if (disposed) us.forEach((u) => u());
      else unsubs.push(...us);
    })();
    return () => {
      disposed = true;
      unsubs.forEach((u) => u());
    };
  }, [session, realm]);

  // Track this device's active source from the supervisor; only `sim` means the
  // headless renderer should serve the contract.
  useEffect(() => {
    if (session === null) return;
    let disposed = false;
    const unsubs: Unsubscribe[] = [];
    const apply = (msg: unknown) => {
      const dev = (msg as DevicesList).devices?.find((d) => d.id === cid);
      setDeviceConfig(dev?.config ?? null);
      setIsSimActive(dev?.active === "sim");
    };
    void (async () => {
      const u = await subscribeLatest(session, supervisorDevices(realm), apply, 4);
      if (disposed) u();
      else unsubs.push(u);
      const cur = await query(session, supervisorDevices(realm), {});
      if (!disposed && cur !== null) apply(cur);
    })();
    return () => {
      disposed = true;
      unsubs.forEach((u) => u());
    };
  }, [session, realm, cid]);

  // Serve the camera2d contract only while this device's source is `sim` (and a
  // session is up). Switching to live/replay/off tears the service down
  // (undeclares queryables + liveliness, stops publishing) so the supervisor's
  // provider — or nothing, for `off` — owns the contract. The service's
  // renderFrame defers to the CameraDriver grab via renderRefs; if a grab
  // arrives before the GL context is live, it waits a tick then retries.
  useEffect(() => {
    if (session === null || !isSimActive) return;
    const service = new Camera2dService({
      session,
      realm,
      cid,
      frameId: opticalFrame(cid),
      renderFrame: async (spec) => {
        // Wait for the renderer to be live (first frame establishes the grab).
        for (let i = 0; grabRef.current === null && i < 200; i++) {
          await delay(25);
        }
        const grab = grabRef.current;
        if (grab === null) throw new Error("renderer not ready");
        // quality is the contract's 1..100 (mozjpeg's range); pass it through.
        return grab(spec.scale, spec.quality);
      },
      streamDefaults: { rate_hz: 15.0, scale: STREAM_RENDER_SCALE, encoding: "jpeg", quality: 75 },
      grabDefaults: { encoding: "jpeg", quality: 90, scale: 1.0 },
      exposureUs,
      gainDb,
    });
    serviceRef.current = service;
    void service.start().catch((e) => console.error("camera2d HAL: service start failed:", e));
    return () => {
      void service.stop();
      serviceRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, realm, cid, isSimActive]);
  return (
    <SimCameraRenderer
      intrinsics={intrinsics}
      flangeRef={flangeRef}
      mountXyz={mountXyz}
      mountRpyDeg={mountRpyDeg}
      baseMatrix={baseMatrix}
      onGrabReady={(grab) => {
        grabRef.current = grab;
      }}
      frames={frames}
      scene={scene}
      jointsRef={jointsRef}
      renderScale={STREAM_RENDER_SCALE}
    />
  );
}
