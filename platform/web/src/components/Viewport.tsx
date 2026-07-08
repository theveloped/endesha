// Live digital twin: URDF robot driven by the joints subscription.
// Bus rate (200 Hz) is decoupled from render rate: the subscription writes
// the latest q into a mutable ref; useFrame applies it per rendered frame.
// Optional `children` render extra scene nodes (frame triads, TCP markers,
// pose ghost) inside the Canvas; `controls` is an absolutely-positioned DOM
// overlay (toggle buttons).
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import {
  useMemo,
  useEffect,
  useState,
  type ReactNode,
  type RefObject,
} from "react";
import URDFLoader, { type URDFRobot } from "urdf-loader";
import type { JointState } from "../lib/messages";
import * as THREE from "three";
import { ZUP_TO_YUP } from "../lib/framemath";

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

interface RobotProps {
  jointsRef: RefObject<JointState | null>;
  onLoaded: () => void;
  selected?: boolean;
  onSelect?: () => void;
}

export function Robot({
  jointsRef,
  onLoaded,
  selected = false,
  onSelect,
}: RobotProps) {
  const [robot, setRobot] = useState<URDFRobot | null>(null);

  useEffect(() => {
    const loader = new URDFLoader();
    loader.packages = { aubo_description: "/aubo_description" };
    loader.load(
      "/aubo_description/aubo_i10.urdf",
      (r) => {
        // URDF limits are ±3.04 rad but the physical robot reaches ±2π on
        // some joints (e.g. shoulder at -4.15 rad for belt poses). The driver
        // enforces real limits; disable the renderer's redundant clamping.
        for (const joint of Object.values(r.joints)) {
          joint.ignoreLimits = true;
        }
        setRobot(r);
        onLoaded();
      },
      undefined,
      (err) => console.error("URDF load failed:", err),
    );
    // Load once; the mounted Canvas owns this robot for the page lifetime.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useFrame(() => {
    const js = jointsRef.current;
    if (robot === null || js === null) return;
    for (let i = 0; i < JOINT_ORDER.length; i++) {
      const joint = robot.joints[JOINT_ORDER[i]];
      if (joint !== undefined) joint.setJointValue(js.q[i]);
    }
  });

  useEffect(() => {
    if (robot === null) return;
    robot.traverse((object) => {
      const mesh = object as THREE.Mesh;
      if (!mesh.isMesh) return;
      const materials = Array.isArray(mesh.material)
        ? mesh.material
        : [mesh.material];
      for (const material of materials) {
        const standard = material as THREE.MeshStandardMaterial;
        if (!standard.emissive) continue;
        standard.emissive.set(selected ? "#0d9488" : "#000000");
        standard.emissiveIntensity = selected ? 0.28 : 0;
      }
    });
  }, [robot, selected]);

  return robot === null ? null : (
    <primitive
      object={robot}
      onClick={(event: { stopPropagation: () => void }) => {
        event.stopPropagation();
        onSelect?.();
      }}
    />
  );
}

export default function Viewport({
  jointsRef,
  children,
  controls,
  topRight,
  baseMatrix = IDENTITY,
  robotSelected = false,
  onRobotSelect,
}: {
  jointsRef: RefObject<JointState | null>;
  children?: ReactNode;
  controls?: ReactNode;
  /** Absolutely-positioned DOM overlay pinned top-right (e.g. the device tree). */
  topRight?: ReactNode;
  /** Robot base pose (Z-up world matrix). The robot + grid render in world;
   *  the robot nests inside this so world (grid) stays the canvas origin. */
  baseMatrix?: THREE.Matrix4;
  robotSelected?: boolean;
  onRobotSelect?: () => void;
}) {
  const [robotLoaded, setRobotLoaded] = useState(false);
  // Orbit around the robot base (in three Y-up coords), not the world origin.
  const target = useMemo<[number, number, number]>(() => {
    const p = new THREE.Vector3()
      .setFromMatrixPosition(baseMatrix)
      .applyEuler(new THREE.Euler(...ZUP_TO_YUP));
    return [p.x, p.y + 0.6, p.z];
  }, [baseMatrix]);

  return (
    <div className="relative h-full min-h-0">
      {!robotLoaded && (
        <div className="absolute inset-0 z-10 flex items-center justify-center text-sm text-muted-foreground">
          loading robot…
        </div>
      )}
      {controls !== undefined && (
        <div className="absolute top-2 left-2 z-10 flex flex-wrap gap-1">
          {controls}
        </div>
      )}
      {topRight !== undefined && (
        <div className="absolute top-2 right-2 z-10">{topRight}</div>
      )}
      <Canvas camera={{ position: [2, 1.6, 2], fov: 50 }}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[3, 6, 3]} intensity={1.2} />
        <gridHelper args={[6, 24, 0x666666, 0x333333]} />
        <group rotation={ZUP_TO_YUP}>
          <group matrix={baseMatrix} matrixAutoUpdate={false}>
            <Robot
              jointsRef={jointsRef}
              onLoaded={() => setRobotLoaded(true)}
              selected={robotSelected}
              onSelect={onRobotSelect}
            />
          </group>
        </group>
        {children}
        <OrbitControls makeDefault target={target} />
      </Canvas>
    </div>
  );
}
