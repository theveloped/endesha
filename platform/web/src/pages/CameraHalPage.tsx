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
//   - intrinsics + mount + resolution: from query params (the headless service
//     passes the cell render block), defaulting to cell.sim.yaml (800x800,
//     fx/fy 900, mount_xyz [0,0,0.05]),
//   - lighting: full ambient + one directional sun (render.py _SUN_POSE),
//   - background: gray 90, scene composition: config/scene/** meshes, with the
//     flange tool and the robot arm OMITTED (an eye-in-hand lens sees neither).
//
// Mounted by headless-main.tsx under headless.html; never in the twin's router.
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import * as THREE from "three";
import { SceneMeshes, FlangeToolMeshes } from "../components/SceneOverlays";
import { Robot } from "../components/Viewport";
import { cameraFromIntrinsics, eyeInHandPose } from "../lib/cameracam";
import {
  connect,
  query,
  subscribeConfigList,
  subscribeLatest,
  type Unsubscribe,
} from "../lib/bus";
import { Camera2dService, type RenderedFrame } from "../lib/camera2d/service";
import { opticalFrame } from "../lib/camera2d/messages";
import { encodeJpeg, initEncoder } from "../lib/camera2d/encode";
import {
  DEFAULT_WS_URL,
  configFramesGlob,
  configSceneGlob,
  stateFlange,
  stateJoints,
  supervisorDevices,
} from "../lib/config";
import { BASE_FRAME, ZUP_TO_YUP, frameWorldMatrix } from "../lib/framemath";
import type {
  DevicesList,
  FlangeState,
  FrameDef,
  Intrinsics,
  JointState,
  Pose,
  SceneObject,
} from "../lib/messages";

// Fallback world<-optical pose (render.py L131-137): straight down from
// board_xyz + [0,0,fallback_height_m] = [0.5,0,0.45], R_wo=diag(1,-1,-1) ==
// quat [1,0,0,0]. Used until the first flange sample arrives.
const FALLBACK_POSE: Pose = { frame: "world", xyz: [0.5, 0, 0.45], quat: [1, 0, 0, 0] };

// render.py global "sun": one directional light, local -Z toward world per
// _SUN_POSE rpy_deg[-30,20,0]. three.js light intensity units differ from
// pyrender's, so this is tuned to give the same shape gradient on textureless
// meshes over a full ambient floor (NOT the twin's [3,6,3]/1.2).
const SUN_DIR = ((): [number, number, number] => {
  // Direction the light travels (local -Z rotated by rpy [-30,20,0] deg, ZYX).
  const e = new THREE.Euler((-30 * Math.PI) / 180, (20 * Math.PI) / 180, 0, "ZYX");
  const d = new THREE.Vector3(0, 0, -1).applyEuler(e);
  // three DirectionalLight points FROM position TO target(origin); position is
  // the negated travel direction. Z-up world coords (nested under ZUP_TO_YUP).
  return [-d.x, -d.y, -d.z];
})();

// Z-up world -> three Y-up, as a quaternion. The scene meshes live under a
// `group rotation={ZUP_TO_YUP}`, but the render camera is set as the root camera
// (no parent group), so this same rotation must be flattened into the camera
// pose by hand — otherwise the camera is rotated 90deg about X relative to the
// scene it views. Matches the parent the FrustumOverlay wraps its frustum in.
const ZUP_TO_YUP_QUAT = new THREE.Quaternion().setFromEuler(
  new THREE.Euler(...ZUP_TO_YUP),
);

// The headless canvas renders at the stream's default scale — NOT the full
// intrinsics. Under software GL (SwiftShader, the Docker target) a full-res
// 800x800 render on every frameloop="always" tick saturates the single main
// thread and starves the stream loop to ~4 Hz even though the JPEG encode is
// only a few ms. Rendering (and reading back + encoding) at the stream scale
// keeps every step small, so the loop sustains the 10-15 Hz contract rate. A
// grab at a different scale resizes off this base (cold path). Mirrors the
// contract's _STREAM_DEFAULTS.scale (0.25); the stream hot path reads the
// canvas directly because its scale equals this.
const STREAM_RENDER_SCALE = 0.25;

/** A render+readback+encode the service calls once per stream tick / grab. The
 *  CameraDriver publishes it via onGrabReady once the GL context is live; the
 *  service awaits it. `scale` is the contract scale (output = intrinsics*scale);
 *  `quality` is the contract's 1..100 JPEG quality (mozjpeg's range). */
type GrabFrame = (scale: number, quality: number) => Promise<RenderedFrame>;

/** Parse a query-param float clamped to [lo,hi]; `def` when absent/invalid. */
function clampNum(raw: string | null, def: number, lo: number, hi: number): number {
  if (raw === null) return def;
  const v = Number(raw);
  if (!Number.isFinite(v)) return def;
  return Math.min(hi, Math.max(lo, v));
}

/** Parse a comma list of N floats from a query param, or the default. */
function vecParam(raw: string | null, def: number[]): number[] {
  if (raw === null) return def;
  const parts = raw.split(",").map((s) => Number(s));
  if (parts.length !== def.length || parts.some((x) => !Number.isFinite(x))) return def;
  return parts;
}

/** Resolve after `ms` milliseconds. */
function delay(ms: number): Promise<void> {
  const { promise, resolve } = Promise.withResolvers<void>();
  setTimeout(resolve, ms);
  return promise;
}

// Drives the active camera each frame from the eye-in-hand pose, and exposes a
// synchronous render+readback+encode `grab` the service calls. The camera is
// posed inside the Z-up group, same as every world-frame overlay.
function CameraDriver({
  intrinsics,
  flangeRef,
  mountXyz,
  mountRpyDeg,
  baseMatrix,
  onGrabReady,
}: {
  intrinsics: Intrinsics;
  flangeRef: React.RefObject<FlangeState | null>;
  mountXyz: number[];
  mountRpyDeg: number[];
  baseMatrix: THREE.Matrix4;
  onGrabReady: (grab: GrabFrame | null) => void;
}) {
  const { gl, set } = useThree();
  const camRef = useRef<THREE.PerspectiveCamera | null>(null);
  if (camRef.current === null) camRef.current = new THREE.PerspectiveCamera();
  // baseMatrix arrives async (after the config-frames fetch) and can change as
  // live frame edits stream in; the grab closure is registered once, so read it
  // through a ref kept current by an effect (updating a ref during render is
  // disallowed).
  const baseMatrixRef = useRef(baseMatrix);
  useEffect(() => {
    baseMatrixRef.current = baseMatrix;
  }, [baseMatrix]);
  // Live WebGL2 context + a reusable RGBA readback buffer sized to the
  // drawing buffer; captured once the canvas exists.
  const gl2Ref = useRef<WebGL2RenderingContext | null>(null);
  const bufRef = useRef<Uint8Array | null>(null);
  // Cached canvases for the cold-path resize (a grab whose `scale` differs from
  // the fixed render scale, e.g. a full-res grab): a source canvas the readback
  // is written into and a destination canvas at the output size. Reused across
  // calls so they never reallocate. The stream hot path never touches these.
  const srcCanvasRef = useRef<{ cv: OffscreenCanvas; ctx: OffscreenCanvasRenderingContext2D } | null>(null);
  const dstCanvasRef = useRef<{ cv: OffscreenCanvas; ctx: OffscreenCanvasRenderingContext2D } | null>(null);

  useEffect(() => {
    if (camRef.current !== null) set({ camera: camRef.current });
  }, [set]);

  useEffect(() => {
    const cv = gl.domElement;
    const ctx =
      (gl.getContext() as WebGL2RenderingContext | null) ?? cv.getContext("webgl2");
    if (ctx !== null) gl2Ref.current = ctx;
    bufRef.current = new Uint8Array(cv.width * cv.height * 4);
    void initEncoder(); // warm the WASM encoder before the first grab
  }, [gl]);

  /** Eye-in-hand optical pose in the ARM-BASE frame (the flange pose `arm_sim`
   *  publishes is base-relative), or the top-down fallback before the first
   *  sample. This is what the FrameHeader carries: the FrustumOverlay re-applies
   *  baseMatrix itself, so the header must stay base-relative (not pre-lifted to
   *  world) or the frustum would double-correct. */
  function headerPose(): Pose {
    const fs = flangeRef.current;
    if (fs === null) return FALLBACK_POSE;
    return eyeInHandPose(fs.pose.xyz, fs.pose.quat, mountXyz, mountRpyDeg);
  }

  /** The same pose lifted into the TRUE world frame (baseMatrix · base-pose),
   *  used to place the render camera. The scene meshes resolve to true world via
   *  frameWorldMatrix, so the camera must too — when world != arm base (base is
   *  translated/rotated), the bare base-frame pose renders from the wrong place.
   *  Both matrices are Z-up world, so this stays the same Z-up "world" pose kind
   *  cameraFromIntrinsics expects. */
  function renderPose(): Pose {
    const fs = flangeRef.current;
    if (fs === null) return FALLBACK_POSE;
    const base = eyeInHandPose(fs.pose.xyz, fs.pose.quat, mountXyz, mountRpyDeg);
    const m = baseMatrixRef.current.clone().multiply(
      new THREE.Matrix4().compose(
        new THREE.Vector3(base.xyz[0], base.xyz[1], base.xyz[2]),
        new THREE.Quaternion(base.quat[0], base.quat[1], base.quat[2], base.quat[3]),
        new THREE.Vector3(1, 1, 1),
      ),
    );
    const pos = new THREE.Vector3();
    const quat = new THREE.Quaternion();
    m.decompose(pos, quat, new THREE.Vector3());
    return { frame: "world", xyz: [pos.x, pos.y, pos.z], quat: [quat.x, quat.y, quat.z, quat.w] };
  }

  /** Apply a pose to the active camera (called every frame so the twin-style
   *  live view tracks the arm, and right before a grab so the readback frame is
   *  posed correctly). */
  function applyPose(pose: Pose): void {
    const cam = camRef.current;
    if (cam === null) return;
    const src = cameraFromIntrinsics(intrinsics, pose);
    // cameraFromIntrinsics returns a Z-up world pose meant to be nested under a
    // `group rotation={ZUP_TO_YUP}`. This camera is the root (unparented) render
    // camera, so flatten that parent rotation into the pose directly: world =
    // ZUP_TO_YUP ∘ pose, i.e. rotate the position and pre-multiply the orientation.
    cam.position.copy(src.position).applyQuaternion(ZUP_TO_YUP_QUAT);
    cam.quaternion.copy(ZUP_TO_YUP_QUAT).multiply(src.quaternion);
    cam.fov = src.fov;
    cam.aspect = src.aspect;
    cam.near = src.near;
    cam.far = src.far;
    cam.updateProjectionMatrix();
  }

  // Continuous render (frameloop="always"): pose the camera every frame so the
  // back buffer always holds a fresh, correctly-posed frame. The grab then just
  // reads that buffer + encodes — NO synchronous gl.render in the grab, which
  // (under SwiftShader) stalls readPixels ~175 ms waiting on the GPU. Reading an
  // already-composited buffer (preserveDrawingBuffer keeps it valid) is ~5 ms.
  useFrame(() => {
    applyPose(renderPose());
  });

  useEffect(() => {
    const grab: GrabFrame = async (scale, quality) => {
      const gl2 = gl2Ref.current;
      if (gl2 === null) throw new Error("camera grab: renderer not initialized");
      // The canvas drawing buffer is already sized to the stream render scale
      // (intrinsics * RENDER_SCALE), so this readback is small and cheap — no
      // full-res readback, no per-tick downsample on the hot path.
      const cw = gl.domElement.width;
      const ch = gl.domElement.height;
      let buf = bufRef.current;
      if (buf === null || buf.length < cw * ch * 4) {
        buf = new Uint8Array(cw * ch * 4);
        bufRef.current = buf;
      }
      // Readback the last continuously-rendered frame (buffer stays valid via
      // preserveDrawingBuffer). No synchronous gl.render here.
      gl2.readPixels(0, 0, cw, ch, gl2.RGBA, gl2.UNSIGNED_BYTE, buf);

      // Output resolution is the contract `scale` applied to the FULL intrinsics
      // (NOT the render buffer), so headers/grabs stay spec-correct regardless of
      // the fixed render resolution.
      const ow = Math.max(1, Math.round(intrinsics.w * scale));
      const oh = Math.max(1, Math.round(intrinsics.h * scale));
      let rgba: Uint8Array;
      if (ow === cw && oh === ch) {
        // Hot path (stream scale == render scale): encode the readback directly.
        rgba = buf.subarray(0, cw * ch * 4);
      } else {
        // Cold path (e.g. a full-res grab from the downscaled stream render):
        // resize render buffer -> output via cached canvases. Off the hot loop,
        // so the one-shot cost is fine; the stream never takes this branch.
        if (srcCanvasRef.current === null || srcCanvasRef.current.cv.width !== cw || srcCanvasRef.current.cv.height !== ch) {
          const cv = new OffscreenCanvas(cw, ch);
          srcCanvasRef.current = { cv, ctx: cv.getContext("2d", { willReadFrequently: true })! };
        }
        if (dstCanvasRef.current === null || dstCanvasRef.current.cv.width !== ow || dstCanvasRef.current.cv.height !== oh) {
          const cv = new OffscreenCanvas(ow, oh);
          dstCanvasRef.current = { cv, ctx: cv.getContext("2d", { willReadFrequently: true })! };
        }
        srcCanvasRef.current.ctx.putImageData(
          new ImageData(new Uint8ClampedArray(buf.subarray(0, cw * ch * 4)), cw, ch),
          0,
          0,
        );
        dstCanvasRef.current.ctx.drawImage(srcCanvasRef.current.cv, 0, 0, ow, oh);
        rgba = new Uint8Array(dstCanvasRef.current.ctx.getImageData(0, 0, ow, oh).data.buffer);
      }
      const jpeg = await encodeJpeg(rgba, ow, oh, quality);
      return { jpeg, w: ow, h: oh, pose: headerPose() };
    };
    onGrabReady(grab);
    return () => onGrabReady(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [gl]);

  return null;
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

  const params = new URLSearchParams(window.location.search);
  const wsUrl = params.get("ws") ?? DEFAULT_WS_URL;
  const realm = params.get("realm") ?? "cell";
  const cid = params.get("cid") ?? "cam0";

  // Render block (cell.sim.yaml cam0 defaults), overridable via query params so
  // the headless service can pass the live cell values.
  const w = Math.round(clampNum(params.get("w"), 800, 1, 8192));
  const h = Math.round(clampNum(params.get("h"), 800, 1, 8192));
  const fx = clampNum(params.get("fx"), 900, 1, 1e5);
  const fy = clampNum(params.get("fy"), 900, 1, 1e5);
  const mountXyz = vecParam(params.get("mount_xyz"), [0, 0, 0.05]);
  const mountRpyDeg = vecParam(params.get("mount_rpy_deg"), [0, 0, 0]);
  const exposureUs = clampNum(params.get("exposure_us"), 10000, 1, 1e9);
  const gainDb = clampNum(params.get("gain_db"), 0, -100, 100);

  const intrinsics: Intrinsics = { fx, fy, cx: (w - 1) / 2, cy: (h - 1) / 2, w, h };

  // Robot base pose (Z-up world matrix) from the config frame tree. The flange
  // pose `arm_sim` publishes is arm-base-relative; this lifts the eye-in-hand
  // camera into true world so it matches the world-frame scene meshes.
  const baseMatrix = useMemo(() => {
    const map = new Map(frames.map((fr) => [fr.name, fr.def]));
    return frameWorldMatrix(map, BASE_FRAME);
  }, [frames]);

  // The drawing buffer (and thus every continuous render + readback) is sized to
  // the stream render scale; the full intrinsics still drive the camera frustum
  // (resolution-independent) and the per-grab output dimensions.
  const rw = Math.max(1, Math.round(w * STREAM_RENDER_SCALE));
  const rh = Math.max(1, Math.round(h * STREAM_RENDER_SCALE));

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
    <div style={{ width: rw, height: rh }}>
      <Canvas
        style={{ width: "100%", height: "100%" }}
        dpr={1}
        frameloop="always"
        // antialias:false is load-bearing for throughput — NOT cosmetic. Under
        // software GL (SwiftShader) the MSAA resolve costs ~75 ms per scene
        // render (vs ~25 ms without), and with frameloop="always" that render
        // runs every rAF, saturating the single main thread and starving the
        // stream loop's setTimeout to ~5 Hz. Disabling MSAA restores the 10-15 Hz
        // contract rate. A sim sensor needs no geometric MSAA anyway (real optics
        // blur, and pyrender's rasterizer is un-antialiased too).
        gl={{ preserveDrawingBuffer: true, antialias: false }}
        onCreated={({ scene: s }) => {
          // render.py background_gray 90.
          s.background = new THREE.Color(90 / 255, 90 / 255, 90 / 255);
        }}
      >
        {/* render.py lighting: full white ambient + one directional sun. */}
        <ambientLight intensity={1.0} />
        <directionalLight position={SUN_DIR} intensity={1.0} />
        <CameraDriver
          intrinsics={intrinsics}
          flangeRef={flangeRef}
          mountXyz={mountXyz}
          mountRpyDeg={mountRpyDeg}
          baseMatrix={baseMatrix}
          onGrabReady={(g) => {
            grabRef.current = g;
          }}
        />
        {/* World-frame scene meshes (flange-frame tools filtered out here). */}
        <SceneMeshes objects={scene} frames={frames} />
        {/* The robot arm + the flange gripper, in the same ZUP_TO_YUP ∘ baseMatrix
            world frame as the camera and scene. An eye-in-hand lens sees the
            gripper up close and the arm when it swings into frame. */}
        <group rotation={ZUP_TO_YUP}>
          <group matrix={baseMatrix} matrixAutoUpdate={false}>
            <Robot jointsRef={jointsRef} onLoaded={() => {}} />
          </group>
        </group>
        <FlangeToolMeshes
          objects={scene}
          flangeRef={flangeRef}
          baseMatrix={baseMatrix}
        />
      </Canvas>
    </div>
  );
}
