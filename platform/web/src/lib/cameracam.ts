// Build a Three.js PerspectiveCamera from OpenCV intrinsics + a world<-optical
// pose, matching the conventions FrustumOverlay (SceneOverlays.tsx) and
// framemath.ts already use. The returned camera is meant to be added INSIDE a
// `group rotation={ZUP_TO_YUP}` by the caller, so a Z-up world pose maps into
// three's Y-up space exactly like every other world-frame overlay.
//
// Spike limitation: cx/cy principal-point offset is ignored (the twin's frustum
// ignores it too); only fy drives the vertical FOV. Off-center projection would
// need camera.setViewOffset — out of scope here.
import * as THREE from "three";
import type { Intrinsics, Pose } from "./messages";

// OpenCV optical (+Z fwd, +Y down) -> three camera (-Z fwd, +Y up): a fixed
// 180deg-about-X rotation post-multiplied onto the optical orientation so the
// three camera looks down optical +Z. Mirrors pyrender's _CV_TO_GL =
// diag(1,-1,-1,1) in render.py L52. Built once.
const R_OPTICAL_TO_GL = new THREE.Quaternion().setFromAxisAngle(
  new THREE.Vector3(1, 0, 0),
  Math.PI,
);

/** PerspectiveCamera matching OpenCV intrinsics + a world<-optical pose.
 *  `pose` is OpenCV optical (+Z fwd, +X right, +Y down). The camera is posed in
 *  the Z-up world group; nest it under `group rotation={ZUP_TO_YUP}`. */
export function cameraFromIntrinsics(
  intr: Intrinsics,
  pose: Pose,
  near = 0.01,
  far = 100.0,
): THREE.PerspectiveCamera {
  // Same half-angle math FrustumOverlay uses: vertical FOV from fy/h.
  const fovDeg = (2 * Math.atan(intr.h / 2 / intr.fy) * 180) / Math.PI;
  const aspect = intr.w / intr.h;
  const cam = new THREE.PerspectiveCamera(fovDeg, aspect, near, far);
  cam.position.set(pose.xyz[0], pose.xyz[1], pose.xyz[2]);
  cam.quaternion
    .set(pose.quat[0], pose.quat[1], pose.quat[2], pose.quat[3])
    .multiply(R_OPTICAL_TO_GL);
  cam.updateProjectionMatrix();
  return cam;
}

const UNIT_SCALE = new THREE.Vector3(1, 1, 1);

/** Compose the world<-optical pose for an eye-in-hand camera from the arm
 *  flange pose and the rigid flange->optical mount, replicating the Python
 *  Renderer.camera_pose (render.py): T_world_optical = T_world_flange ·
 *  T_flange_optical. `flangeXyz`/`flangeQuat` are the arm state/flange pose
 *  (quat scalar-last [x,y,z,w]); `mountXyz`/`mountRpyDeg` come from the camera
 *  resource render block (mount_xyz [0,0,0.05], mount_rpy_deg [0,0,0] in sim).
 *  Returns an OpenCV-optical world pose (the same convention cameraFromIntrinsics
 *  and the FrameHeader.pose use). */
export function eyeInHandPose(
  flangeXyz: number[],
  flangeQuat: number[],
  mountXyz: number[],
  mountRpyDeg: number[],
): Pose {
  const tWorldFlange = new THREE.Matrix4().compose(
    new THREE.Vector3(flangeXyz[0], flangeXyz[1], flangeXyz[2]),
    new THREE.Quaternion(flangeQuat[0], flangeQuat[1], flangeQuat[2], flangeQuat[3]),
    UNIT_SCALE,
  );
  // rpy_deg_to_matrix: R = Rz(yaw)·Ry(pitch)·Rx(roll). Three's Euler with
  // order "ZYX" composes the body rotations in that exact order; roll/pitch/yaw
  // stay in .x/.y/.z.
  const e = new THREE.Euler(
    (mountRpyDeg[0] * Math.PI) / 180,
    (mountRpyDeg[1] * Math.PI) / 180,
    (mountRpyDeg[2] * Math.PI) / 180,
    "ZYX",
  );
  const tFlangeOptical = new THREE.Matrix4().compose(
    new THREE.Vector3(mountXyz[0], mountXyz[1], mountXyz[2]),
    new THREE.Quaternion().setFromEuler(e),
    UNIT_SCALE,
  );
  const tWorldOptical = tWorldFlange.multiply(tFlangeOptical);
  const pos = new THREE.Vector3();
  const quat = new THREE.Quaternion();
  tWorldOptical.decompose(pos, quat, new THREE.Vector3());
  return {
    frame: "world",
    xyz: [pos.x, pos.y, pos.z],
    quat: [quat.x, quat.y, quat.z, quat.w],
  };
}
