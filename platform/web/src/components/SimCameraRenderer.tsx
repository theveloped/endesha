import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useRef } from "react";
import * as THREE from "three";
import { FlangeToolMeshes, SceneMeshes } from "./SceneOverlays";
import { Robot } from "./Viewport";
import { cameraFromIntrinsics, eyeInHandPose } from "../lib/cameracam";
import { encodeJpeg, initEncoder } from "../lib/camera2d/encode";
import type { RenderedFrame } from "../lib/camera2d/service";
import { ZUP_TO_YUP } from "../lib/framemath";
import type {
  FlangeState,
  FrameDef,
  Intrinsics,
  JointState,
  Pose,
  SceneObject,
} from "../lib/messages";

const FALLBACK_POSE: Pose = {
  frame: "world",
  xyz: [0.5, 0, 0.45],
  quat: [1, 0, 0, 0],
};

const SUN_DIR = ((): [number, number, number] => {
  const e = new THREE.Euler((-30 * Math.PI) / 180, (20 * Math.PI) / 180, 0, "ZYX");
  const d = new THREE.Vector3(0, 0, -1).applyEuler(e);
  return [-d.x, -d.y, -d.z];
})();

const ZUP_TO_YUP_QUAT = new THREE.Quaternion().setFromEuler(
  new THREE.Euler(...ZUP_TO_YUP),
);

export type GrabFrame = (scale: number, quality: number) => Promise<RenderedFrame>;

interface DriverProps {
  intrinsics: Intrinsics;
  flangeRef: React.RefObject<FlangeState | null>;
  mountXyz: number[];
  mountRpyDeg: number[];
  baseMatrix: THREE.Matrix4;
  onGrabReady: (grab: GrabFrame | null) => void;
}

function CameraDriver({
  intrinsics,
  flangeRef,
  mountXyz,
  mountRpyDeg,
  baseMatrix,
  onGrabReady,
}: DriverProps) {
  const { gl, set } = useThree();
  const camRef = useRef<THREE.PerspectiveCamera | null>(null);
  if (camRef.current === null) camRef.current = new THREE.PerspectiveCamera();
  const baseMatrixRef = useRef(baseMatrix);
  const gl2Ref = useRef<WebGL2RenderingContext | null>(null);
  const bufRef = useRef<Uint8Array | null>(null);
  const srcCanvasRef = useRef<{
    cv: OffscreenCanvas;
    ctx: OffscreenCanvasRenderingContext2D;
  } | null>(null);
  const dstCanvasRef = useRef<{
    cv: OffscreenCanvas;
    ctx: OffscreenCanvasRenderingContext2D;
  } | null>(null);

  useEffect(() => {
    baseMatrixRef.current = baseMatrix;
  }, [baseMatrix]);

  useEffect(() => {
    if (camRef.current !== null) set({ camera: camRef.current });
  }, [set]);

  useEffect(() => {
    const cv = gl.domElement;
    const ctx =
      (gl.getContext() as WebGL2RenderingContext | null) ?? cv.getContext("webgl2");
    if (ctx !== null) gl2Ref.current = ctx;
    bufRef.current = new Uint8Array(cv.width * cv.height * 4);
    void initEncoder();
  }, [gl]);

  function headerPose(): Pose {
    const fs = flangeRef.current;
    return fs === null
      ? FALLBACK_POSE
      : eyeInHandPose(fs.pose.xyz, fs.pose.quat, mountXyz, mountRpyDeg);
  }

  function renderPose(): Pose {
    const fs = flangeRef.current;
    if (fs === null) return FALLBACK_POSE;
    const base = eyeInHandPose(fs.pose.xyz, fs.pose.quat, mountXyz, mountRpyDeg);
    const matrix = baseMatrixRef.current.clone().multiply(
      new THREE.Matrix4().compose(
        new THREE.Vector3(...base.xyz),
        new THREE.Quaternion(...base.quat),
        new THREE.Vector3(1, 1, 1),
      ),
    );
    const pos = new THREE.Vector3();
    const quat = new THREE.Quaternion();
    matrix.decompose(pos, quat, new THREE.Vector3());
    return {
      frame: "world",
      xyz: [pos.x, pos.y, pos.z],
      quat: [quat.x, quat.y, quat.z, quat.w],
    };
  }

  function applyPose(pose: Pose): void {
    const cam = camRef.current;
    if (cam === null) return;
    const src = cameraFromIntrinsics(intrinsics, pose);
    cam.position.copy(src.position).applyQuaternion(ZUP_TO_YUP_QUAT);
    cam.quaternion.copy(ZUP_TO_YUP_QUAT).multiply(src.quaternion);
    cam.fov = src.fov;
    cam.aspect = src.aspect;
    cam.near = src.near;
    cam.far = src.far;
    cam.updateProjectionMatrix();
  }

  useFrame(() => applyPose(renderPose()));

  useEffect(() => {
    const grab: GrabFrame = async (scale, quality) => {
      const gl2 = gl2Ref.current;
      if (gl2 === null) throw new Error("camera grab: renderer not initialized");
      const cw = gl.domElement.width;
      const ch = gl.domElement.height;
      let buf = bufRef.current;
      if (buf === null || buf.length < cw * ch * 4) {
        buf = new Uint8Array(cw * ch * 4);
        bufRef.current = buf;
      }
      gl2.readPixels(0, 0, cw, ch, gl2.RGBA, gl2.UNSIGNED_BYTE, buf);
      const ow = Math.max(1, Math.round(intrinsics.w * scale));
      const oh = Math.max(1, Math.round(intrinsics.h * scale));
      let rgba: Uint8Array;
      if (ow === cw && oh === ch) {
        rgba = buf.subarray(0, cw * ch * 4);
      } else {
        if (
          srcCanvasRef.current === null ||
          srcCanvasRef.current.cv.width !== cw ||
          srcCanvasRef.current.cv.height !== ch
        ) {
          const cv = new OffscreenCanvas(cw, ch);
          srcCanvasRef.current = {
            cv,
            ctx: cv.getContext("2d", { willReadFrequently: true })!,
          };
        }
        if (
          dstCanvasRef.current === null ||
          dstCanvasRef.current.cv.width !== ow ||
          dstCanvasRef.current.cv.height !== oh
        ) {
          const cv = new OffscreenCanvas(ow, oh);
          dstCanvasRef.current = {
            cv,
            ctx: cv.getContext("2d", { willReadFrequently: true })!,
          };
        }
        srcCanvasRef.current.ctx.putImageData(
          new ImageData(new Uint8ClampedArray(buf.subarray(0, cw * ch * 4)), cw, ch),
          0,
          0,
        );
        dstCanvasRef.current.ctx.drawImage(srcCanvasRef.current.cv, 0, 0, ow, oh);
        rgba = new Uint8Array(
          dstCanvasRef.current.ctx.getImageData(0, 0, ow, oh).data.buffer,
        );
      }
      return {
        jpeg: await encodeJpeg(rgba, ow, oh, quality),
        w: ow,
        h: oh,
        pose: headerPose(),
      };
    };
    onGrabReady(grab);
    return () => onGrabReady(null);
  }, [gl, intrinsics, onGrabReady]);

  return null;
}

interface SimCameraRendererProps extends DriverProps {
  frames: { name: string; def: FrameDef }[];
  scene: { name: string; obj: SceneObject }[];
  jointsRef: React.RefObject<JointState | null>;
  renderScale: number;
}

export function SimCameraRenderer({
  frames,
  scene,
  jointsRef,
  renderScale,
  ...driver
}: SimCameraRendererProps) {
  const rw = Math.max(1, Math.round(driver.intrinsics.w * renderScale));
  const rh = Math.max(1, Math.round(driver.intrinsics.h * renderScale));
  return (
    <div style={{ width: rw, height: rh }}>
      <Canvas
        style={{ width: "100%", height: "100%" }}
        dpr={1}
        frameloop="always"
        gl={{ preserveDrawingBuffer: true, antialias: false }}
        onCreated={({ scene: threeScene }) => {
          threeScene.background = new THREE.Color(90 / 255, 90 / 255, 90 / 255);
        }}
      >
        <ambientLight intensity={1} />
        <directionalLight position={SUN_DIR} intensity={1} />
        <CameraDriver {...driver} />
        <SceneMeshes objects={scene} frames={frames} />
        <group rotation={ZUP_TO_YUP}>
          <group matrix={driver.baseMatrix} matrixAutoUpdate={false}>
            <Robot jointsRef={jointsRef} onLoaded={() => {}} />
          </group>
        </group>
        <FlangeToolMeshes
          objects={scene}
          flangeRef={driver.flangeRef}
          baseMatrix={driver.baseMatrix}
        />
      </Canvas>
    </div>
  );
}
