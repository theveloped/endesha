// 3D overlays for the digital twin: static frame-tree triads, a live active-
// TCP tip marker, and a translucent ghost robot for stored-pose preview.
// World-frame overlays (frame triads, scene meshes, camera frustum) render at
// their world poses; the robot and base-frame overlays (TCP marker/gizmo, pose
// ghost) nest a base-frame matrix inside the Z-up -> three Y-up group, so they
// stay correct now that world is separated from the robot base.
import { Html, TransformControls, useGLTF } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import {
  Component,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import * as THREE from "three";
import URDFLoader, { type URDFRobot } from "urdf-loader";
import type {
  FlangeState,
  FrameDef,
  Intrinsics,
  Pose,
  SceneGeometry,
  SceneObject,
  TcpDef,
} from "../lib/messages";
import { ZUP_TO_YUP, frameWorldMatrix, FLANGE_FRAME } from "../lib/framemath";
import { assetUrl } from "../lib/config";

// URDF joint names in wire order (wf/hal/aubo_i10/fk.py JOINT_ORDER).
const JOINT_ORDER = [
  "shoulder_joint",
  "upperArm_joint",
  "foreArm_joint",
  "wrist1_joint",
  "wrist2_joint",
  "wrist3_joint",
];

const IDENTITY = new THREE.Matrix4();

function tcpOffsetMatrix(def: TcpDef): THREE.Matrix4 {
  return new THREE.Matrix4().compose(
    new THREE.Vector3(def.xyz[0], def.xyz[1], def.xyz[2]),
    new THREE.Quaternion(def.quat[0], def.quat[1], def.quat[2], def.quat[3]),
    new THREE.Vector3(1, 1, 1),
  );
}

const LABEL_STYLE: React.CSSProperties = {
  pointerEvents: "none",
  fontFamily: "var(--font-mono, monospace)",
  fontSize: "10px",
  whiteSpace: "nowrap",
  color: "#e5e7eb",
  background: "rgba(0,0,0,0.45)",
  padding: "0 3px",
  borderRadius: "3px",
  transform: "translate(8px, -8px)",
};

interface FrameTriadsProps {
  frames: { name: string; def: FrameDef }[];
  /** Triad axis length (m). */
  size?: number;
}

/** Static RGB=XYZ triads at every frame, rendered at their WORLD poses (canvas
 *  origin = world). The robot base frame's triad lands on the robot. */
export function FrameTriads({ frames, size = 0.12 }: FrameTriadsProps) {
  const placed = useMemo(() => {
    const map = new Map(frames.map((f) => [f.name, f.def]));
    return frames.map(({ name }) => {
      const m = frameWorldMatrix(map, name);
      const pos = new THREE.Vector3();
      const quat = new THREE.Quaternion();
      m.decompose(pos, quat, new THREE.Vector3());
      return { name, pos, quat };
    });
  }, [frames]);

  return (
    <group rotation={ZUP_TO_YUP}>
      {placed.map(({ name, pos, quat }) => (
        <group
          key={name}
          position={[pos.x, pos.y, pos.z]}
          quaternion={[quat.x, quat.y, quat.z, quat.w]}
        >
          <axesHelper args={[size]} />
          <Html center style={LABEL_STYLE}>
            {name}
          </Html>
        </group>
      ))}
    </group>
  );
}

interface TcpTipMarkerProps {
  flangeRef: RefObject<FlangeState | null>;
  tcpDef: TcpDef;
  label?: string;
  /** Robot base pose (Z-up world matrix); the marker nests inside it. */
  baseMatrix?: THREE.Matrix4;
}

/** Live marker at flange ∘ TCP-offset (flange pose is already in base frame). */
export function TcpTipMarker({
  flangeRef,
  tcpDef,
  label,
  baseMatrix = IDENTITY,
}: TcpTipMarkerProps) {
  const groupRef = useRef<THREE.Group>(null);
  const offset = useMemo(() => tcpOffsetMatrix(tcpDef), [tcpDef]);
  const tmp = useMemo(
    () => ({
      flange: new THREE.Matrix4(),
      tip: new THREE.Matrix4(),
      pos: new THREE.Vector3(),
      quat: new THREE.Quaternion(),
      scale: new THREE.Vector3(),
      v: new THREE.Vector3(),
      q: new THREE.Quaternion(),
    }),
    [],
  );

  useFrame(() => {
    const g = groupRef.current;
    const fs = flangeRef.current;
    if (g === null || fs === null) return;
    const p = fs.pose;
    tmp.flange.compose(
      tmp.v.set(p.xyz[0], p.xyz[1], p.xyz[2]),
      tmp.q.set(p.quat[0], p.quat[1], p.quat[2], p.quat[3]),
      tmp.scale.set(1, 1, 1),
    );
    tmp.tip.multiplyMatrices(tmp.flange, offset);
    tmp.tip.decompose(tmp.pos, tmp.quat, tmp.scale);
    g.position.copy(tmp.pos);
    g.quaternion.copy(tmp.quat);
  });

  return (
    <group rotation={ZUP_TO_YUP}>
      <group matrix={baseMatrix} matrixAutoUpdate={false}>
        <group ref={groupRef}>
          <mesh>
            <sphereGeometry args={[0.014, 16, 16]} />
            <meshStandardMaterial color="#22d3ee" emissive="#0e7490" />
          </mesh>
          <axesHelper args={[0.09]} />
          {label !== undefined && (
            <Html center style={LABEL_STYLE}>
              {label}
            </Html>
          )}
        </group>
      </group>
    </group>
  );
}

interface TcpDragControlsProps {
  flangeRef: RefObject<FlangeState | null>;
  /** Active-TCP offset def; null ⇒ flange (identity offset). */
  tcpDef: TcpDef | null;
  mode: "translate" | "rotate";
  /** A goal is in flight — freeze idle live-sync. */
  pending: boolean;
  /** Called on release with the dragged TCP pose in base frame. */
  onCommit: (
    xyz: [number, number, number],
    quat: [number, number, number, number],
  ) => void;
  /** Robot base pose (Z-up world matrix); the gizmo target nests inside it, so
   *  its local pose stays base-frame and commits unchanged. */
  baseMatrix?: THREE.Matrix4;
}

/** Interactive gizmo on the active TCP: drag a translate/rotate handle, and on
 *  release commit the dragged base-frame pose. The target group is nested in
 *  the Z-up group, so its local position/quaternion ARE base-frame (Z-up)
 *  coordinates — read back directly regardless of handle `space`. When idle
 *  (not dragging, no goal pending) the target snaps to the live TCP each frame
 *  so it tracks the robot and re-anchors after a move or a rejection. */
export function TcpDragControls({
  flangeRef,
  tcpDef,
  mode,
  pending,
  onCommit,
  baseMatrix = IDENTITY,
}: TcpDragControlsProps) {
  // Callback ref (state, not a ref): TransformControls mounts only once the
  // target group exists (drei attaches via `object`; plain refs aren't reactive).
  const [target, setTarget] = useState<THREE.Group | null>(null);
  const draggingRef = useRef(false);
  const offset = useMemo(
    () => (tcpDef !== null ? tcpOffsetMatrix(tcpDef) : new THREE.Matrix4()),
    [tcpDef],
  );
  const tmp = useMemo(
    () => ({
      flange: new THREE.Matrix4(),
      tip: new THREE.Matrix4(),
      pos: new THREE.Vector3(),
      quat: new THREE.Quaternion(),
      scale: new THREE.Vector3(),
      v: new THREE.Vector3(),
      q: new THREE.Quaternion(),
    }),
    [],
  );

  // Compose the live active-TCP pose (flange ∘ offset, already base-frame) into
  // `out.pos`/`out.quat`; false when no flange sample yet. Called only from
  // useFrame and the release handler — never during render, so the ref read
  // stays out of the render path (react-hooks/refs).
  const liveTcp = useCallback(
    (out: typeof tmp): boolean => {
      const fs = flangeRef.current;
      if (fs === null) return false;
      const p = fs.pose;
      out.flange.compose(
        out.v.set(p.xyz[0], p.xyz[1], p.xyz[2]),
        out.q.set(p.quat[0], p.quat[1], p.quat[2], p.quat[3]),
        out.scale.set(1, 1, 1),
      );
      out.tip.multiplyMatrices(out.flange, offset);
      out.tip.decompose(out.pos, out.quat, out.scale);
      return true;
    },
    [flangeRef, offset],
  );

  useFrame(() => {
    if (target === null || draggingRef.current || pending) return;
    if (liveTcp(tmp)) {
      target.position.copy(tmp.pos);
      target.quaternion.copy(tmp.quat);
    }
  });

  const handleRelease = () => {
    draggingRef.current = false;
    if (target === null) return;
    const desiredPos = target.position; // base-frame xyz (parent-local)
    const desiredQuat = target.quaternion; // base-frame quat
    if (!liveTcp(tmp)) return; // no flange sample yet → ignore
    const dPos = desiredPos.distanceTo(tmp.pos);
    const dAng = 2 * Math.acos(Math.min(1, Math.abs(desiredQuat.dot(tmp.quat))));
    if (dPos < 1e-3 && dAng < 0.0087) return; // <1 mm and <0.5° — click, not drag
    onCommit(
      [desiredPos.x, desiredPos.y, desiredPos.z],
      [desiredQuat.x, desiredQuat.y, desiredQuat.z, desiredQuat.w],
    );
  };

  return (
    <>
      <group rotation={ZUP_TO_YUP}>
        <group matrix={baseMatrix} matrixAutoUpdate={false}>
          <group ref={setTarget}>
            <mesh>
              <sphereGeometry args={[0.012, 16, 16]} />
              <meshStandardMaterial color="#f472b6" emissive="#9d174d" />
            </mesh>
            <axesHelper args={[0.12]} />
          </group>
        </group>
      </group>
      {target !== null && (
        <TransformControls
          object={target}
          mode={mode}
          space="world"
          size={0.75}
          onMouseDown={() => {
            draggingRef.current = true;
          }}
          onMouseUp={handleRelease}
        />
      )}
    </>
  );
}

/** Translucent robot posed at a stored joint configuration (preview only). */
export function PoseGhost({
  q,
  baseMatrix = IDENTITY,
}: {
  q: number[];
  baseMatrix?: THREE.Matrix4;
}) {
  const robotRef = useRef<URDFRobot | null>(null);
  const groupRef = useRef<THREE.Group>(null);

  useEffect(() => {
    const group = groupRef.current;
    const loader = new URDFLoader();
    loader.packages = { aubo_description: "/aubo_description" };
    let disposed = false;
    loader.load(
      "/aubo_description/aubo_i10.urdf",
      (r) => {
        if (disposed) return;
        r.traverse((o) => {
          const mesh = o as THREE.Mesh;
          if (mesh.isMesh) {
            const mats = Array.isArray(mesh.material)
              ? mesh.material
              : [mesh.material];
            for (const m of mats) {
              const mat = m as THREE.MeshStandardMaterial;
              mat.transparent = true;
              mat.opacity = 0.3;
              mat.depthWrite = false;
              mat.color = new THREE.Color("#38bdf8");
            }
          }
        });
        robotRef.current = r;
        group?.add(r);
        applyJoints(r, q);
      },
      undefined,
      (err) => console.error("ghost URDF load failed:", err),
    );
    return () => {
      disposed = true;
      const r = robotRef.current;
      if (r !== null) {
        group?.remove(r);
        robotRef.current = null;
      }
    };
    // Load once; joint updates handled by the effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (robotRef.current !== null) applyJoints(robotRef.current, q);
  }, [q]);

  return (
    <group rotation={ZUP_TO_YUP}>
      <group matrix={baseMatrix} matrixAutoUpdate={false}>
        <group ref={groupRef} />
      </group>
    </group>
  );
}

function applyJoints(robot: URDFRobot, q: number[]): void {
  for (let i = 0; i < JOINT_ORDER.length; i++) {
    const joint = robot.joints[JOINT_ORDER[i]];
    if (joint !== undefined) joint.setJointValue(q[i]);
  }
}

interface FrustumOverlayProps {
  /** Camera optical intrinsics (FOV); null ⇒ hidden. */
  intrinsics: Intrinsics | null;
  /** Latest per-frame world<-optical camera pose; null ⇒ hidden. */
  poseRef: RefObject<Pose | null>;
  /** Far plane distance (m). Near is a small fixed fraction. */
  far?: number;
}

/** Wireframe view frustum of the camera at its captured pose.
 *
 *  Built from the intrinsics FOV (half-angles atan((w/2)/fx), atan((h/2)/fy))
 *  as a near+far rectangle joined by four corner rays, in OpenCV optical axes
 *  (+Z forward, +X right, +Y down). The group is posed at the per-frame
 *  world<-optical pose INSIDE the Z-up group, so optical axes map straight into
 *  base frame (== world in v0). Hidden until both intrinsics and a pose exist. */
export function FrustumOverlay({
  intrinsics,
  poseRef,
  far = 0.6,
}: FrustumOverlayProps) {
  const groupRef = useRef<THREE.Group>(null);
  const tmp = useMemo(
    () => ({ v: new THREE.Vector3(), q: new THREE.Quaternion() }),
    [],
  );

  // Corner-ray line segments in optical frame, derived from the intrinsics.
  const geometry = useMemo(() => {
    if (intrinsics === null) return null;
    const near = Math.min(0.05, far * 0.1);
    const txN = (near * (intrinsics.w / 2)) / intrinsics.fx;
    const tyN = (near * (intrinsics.h / 2)) / intrinsics.fy;
    const txF = (far * (intrinsics.w / 2)) / intrinsics.fx;
    const tyF = (far * (intrinsics.h / 2)) / intrinsics.fy;
    // Near corners (z=near), far corners (z=far): TL,TR,BR,BL.
    const nc: [number, number, number][] = [
      [-txN, -tyN, near], [txN, -tyN, near], [txN, tyN, near], [-txN, tyN, near],
    ];
    const fc: [number, number, number][] = [
      [-txF, -tyF, far], [txF, -tyF, far], [txF, tyF, far], [-txF, tyF, far],
    ];
    const seg: number[] = [];
    const edge = (a: number[], b: number[]) => seg.push(...a, ...b);
    for (let i = 0; i < 4; i++) {
      edge(nc[i], nc[(i + 1) % 4]); // near rectangle
      edge(fc[i], fc[(i + 1) % 4]); // far rectangle
      edge(nc[i], fc[i]); // corner ray
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(seg, 3));
    return g;
  }, [intrinsics, far]);

  useFrame(() => {
    const g = groupRef.current;
    if (g === null) return;
    const p = poseRef.current;
    const visible = p !== null && geometry !== null;
    g.visible = visible;
    if (!visible || p === null) return;
    g.position.copy(tmp.v.set(p.xyz[0], p.xyz[1], p.xyz[2]));
    g.quaternion.copy(tmp.q.set(p.quat[0], p.quat[1], p.quat[2], p.quat[3]));
  });

  if (geometry === null) return null;
  return (
    <group rotation={ZUP_TO_YUP}>
      <group ref={groupRef} visible={false}>
        <lineSegments>
          <primitive object={geometry} attach="geometry" />
          <lineBasicMaterial color="#f59e0b" />
        </lineSegments>
      </group>
    </group>
  );
}

// ── Static scene meshes (CAD cell import, config/scene/**) ───────────────────

/** A cached GLB asset, cloned so multiple placements of one mesh (e.g. the
 *  1590 bracket ×3) don't share a single scene-graph node. */
function MeshAsset({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={useMemo(() => scene.clone(true), [scene])} />;
}

/** Render a scene primitive in a neutral material. Coal's cylinder axis is Z;
 *  three's is Y, so rotate the cylinder so its length runs along Z to match. */
function PrimitiveMesh({ geometry }: { geometry: SceneGeometry }) {
  const material = <meshStandardMaterial color="#9aa0a6" />;
  if (geometry.type === "box") {
    const [sx, sy, sz] = geometry.size ?? [0.1, 0.1, 0.1];
    return (
      <mesh>
        <boxGeometry args={[sx, sy, sz]} />
        {material}
      </mesh>
    );
  }
  if (geometry.type === "cylinder") {
    const r = geometry.radius ?? 0.05;
    const l = geometry.length ?? 0.1;
    return (
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <cylinderGeometry args={[r, r, l, 24]} />
        {material}
      </mesh>
    );
  }
  if (geometry.type === "sphere") {
    const r = geometry.radius ?? 0.05;
    return (
      <mesh>
        <sphereGeometry args={[r, 24, 16]} />
        {material}
      </mesh>
    );
  }
  return null;
}

/** A missing/bad GLB skips just that object instead of blanking the Canvas,
 *  mirroring the backend "skip bad asset" policy (collision._scene_geometry). */
class MeshErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    // swallow: one bad asset must not take down the twin
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

interface SceneMeshesProps {
  objects: { name: string; obj: SceneObject }[];
  frames: { name: string; def: FrameDef }[];
  visible?: boolean;
}

/** Static `config/scene/**` geometry, rendered relative to `world` (canvas
 *  origin = world = robot base, matching collision + sim camera). Unlike
 *  FrameTriads this does NOT apply baseInv: object poses are already in the
 *  robot-base frame, so a bare frameWorldMatrix ∘ local-pose is correct. */
export function SceneMeshes({
  objects,
  frames,
  visible = true,
}: SceneMeshesProps) {
  const placed = useMemo(() => {
    const map = new Map(frames.map((f) => [f.name, f.def]));
    // Flange-frame objects are end-of-arm tools drawn by FlangeToolMeshes; skip
    // them here (frameWorldMatrix returns identity for the unknown flange frame,
    // which would otherwise place them at the world origin).
    return objects
      .filter(({ obj }) => obj.frame !== FLANGE_FRAME)
      .map(({ name, obj }) => {
      const m = frameWorldMatrix(map, obj.frame)
        .clone()
        .multiply(
          new THREE.Matrix4().compose(
            new THREE.Vector3(
              obj.pose.xyz[0],
              obj.pose.xyz[1],
              obj.pose.xyz[2],
            ),
            new THREE.Quaternion(
              obj.pose.quat[0],
              obj.pose.quat[1],
              obj.pose.quat[2],
              obj.pose.quat[3],
            ),
            new THREE.Vector3(1, 1, 1),
          ),
        );
      const pos = new THREE.Vector3();
      const quat = new THREE.Quaternion();
      m.decompose(pos, quat, new THREE.Vector3());
      return { name, obj, pos, quat };
    });
  }, [objects, frames]);

  if (!visible) return null;
  return (
    <group rotation={ZUP_TO_YUP}>
      {placed.map(({ name, obj, pos, quat }) => (
        <group
          key={name}
          position={[pos.x, pos.y, pos.z]}
          quaternion={[quat.x, quat.y, quat.z, quat.w]}
        >
          {obj.geometry.type === "mesh" && obj.geometry.uri ? (
            <MeshErrorBoundary>
              <Suspense fallback={null}>
                <MeshAsset url={assetUrl(obj.geometry.uri)} />
              </Suspense>
            </MeshErrorBoundary>
          ) : (
            <PrimitiveMesh geometry={obj.geometry} />
          )}
        </group>
      ))}
    </group>
  );
}

interface FlangeToolMeshesProps {
  objects: { name: string; obj: SceneObject }[];
  flangeRef: RefObject<FlangeState | null>;
  baseMatrix?: THREE.Matrix4;
  visible?: boolean;
}

/** End-of-arm tools (config/scene objects with frame === FLANGE_FRAME) rendered
 *  rigidly attached to the LIVE flange: world = ZUP_TO_YUP ∘ baseMatrix ∘
 *  flangePose(base) ∘ mountPose(obj.pose). The flange group is updated every
 *  frame from flangeRef (same as TcpTipMarker); each tool mesh nests inside it
 *  at its static mount pose. */
export function FlangeToolMeshes({
  objects,
  flangeRef,
  baseMatrix = IDENTITY,
  visible = true,
}: FlangeToolMeshesProps) {
  const tools = useMemo(
    () =>
      objects.filter(
        ({ obj }) =>
          obj.frame === FLANGE_FRAME &&
          obj.geometry.type === "mesh" &&
          obj.geometry.uri,
      ),
    [objects],
  );
  const groupRef = useRef<THREE.Group>(null);
  const tmp = useMemo(
    () => ({
      flange: new THREE.Matrix4(),
      pos: new THREE.Vector3(),
      quat: new THREE.Quaternion(),
      scale: new THREE.Vector3(),
      v: new THREE.Vector3(),
      q: new THREE.Quaternion(),
    }),
    [],
  );

  useFrame(() => {
    const g = groupRef.current;
    const fs = flangeRef.current;
    if (g === null || fs === null) return;
    const p = fs.pose;
    tmp.flange.compose(
      tmp.v.set(p.xyz[0], p.xyz[1], p.xyz[2]),
      tmp.q.set(p.quat[0], p.quat[1], p.quat[2], p.quat[3]),
      tmp.scale.set(1, 1, 1),
    );
    tmp.flange.decompose(tmp.pos, tmp.quat, tmp.scale);
    g.position.copy(tmp.pos);
    g.quaternion.copy(tmp.quat);
  });

  if (!visible || tools.length === 0) return null;
  return (
    <group rotation={ZUP_TO_YUP}>
      <group matrix={baseMatrix} matrixAutoUpdate={false}>
        <group ref={groupRef}>
          {tools.map(({ name, obj }) => (
            <group
              key={name}
              position={[obj.pose.xyz[0], obj.pose.xyz[1], obj.pose.xyz[2]]}
              quaternion={[
                obj.pose.quat[0],
                obj.pose.quat[1],
                obj.pose.quat[2],
                obj.pose.quat[3],
              ]}
            >
              <MeshErrorBoundary>
                <Suspense fallback={null}>
                  <MeshAsset url={assetUrl(obj.geometry.uri!)} />
                </Suspense>
              </MeshErrorBoundary>
            </group>
          ))}
        </group>
      </group>
    </group>
  );
}
