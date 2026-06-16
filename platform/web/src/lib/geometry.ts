// Minimal rotation helper for pose-target entry. Source of truth:
// wf.core.frames.rpy_to_matrix (python) — extrinsic XYZ convention,
// R = Rz(yaw) @ Ry(pitch) @ Rx(roll); quaternions scalar-last [qx,qy,qz,qw].

const DEG_TO_RAD = Math.PI / 180;

/** Roll/pitch/yaw in DEGREES -> unit quaternion [qx, qy, qz, qw]. */
export function rpyDegToQuat(
  r: number,
  p: number,
  y: number,
): [number, number, number, number] {
  const roll = r * DEG_TO_RAD;
  const pitch = p * DEG_TO_RAD;
  const yaw = y * DEG_TO_RAD;
  const cr = Math.cos(roll / 2);
  const sr = Math.sin(roll / 2);
  const cp = Math.cos(pitch / 2);
  const sp = Math.sin(pitch / 2);
  const cy = Math.cos(yaw / 2);
  const sy = Math.sin(yaw / 2);
  // q = qz(yaw) * qy(pitch) * qx(roll), Hamilton product expanded.
  return [
    sr * cp * cy - cr * sp * sy,
    cr * sp * cy + sr * cp * sy,
    cr * cp * sy - sr * sp * cy,
    cr * cp * cy + sr * sp * sy,
  ];
}

const RAD_TO_DEG = 180 / Math.PI;

/**
 * Inverse of {@link rpyDegToQuat}: unit quaternion [qx,qy,qz,qw] -> roll/
 * pitch/yaw in DEGREES, same extrinsic-XYZ convention (R = Rz·Ry·Rx).
 * Used to pre-fill edit forms from stored quaternions.
 */
export function quatToRpyDeg(
  q: number[],
): [number, number, number] {
  const [x, y, z, w] = q;
  // Rotation-matrix entries needed for the ZYX-intrinsic extraction.
  const r00 = 1 - 2 * (y * y + z * z);
  const r10 = 2 * (x * y + w * z);
  const r20 = 2 * (x * z - w * y);
  const r21 = 2 * (y * z + w * x);
  const r22 = 1 - 2 * (x * x + y * y);
  const pitch = Math.asin(Math.max(-1, Math.min(1, -r20)));
  let roll: number;
  let yaw: number;
  if (Math.abs(r20) < 1 - 1e-9) {
    roll = Math.atan2(r21, r22);
    yaw = Math.atan2(r10, r00);
  } else {
    // Gimbal lock (pitch = ±90°): fold roll into yaw.
    roll = 0;
    const r01 = 2 * (x * y - w * z);
    const r11 = 1 - 2 * (x * x + z * z);
    yaw = Math.atan2(-r01, r11);
  }
  return [roll * RAD_TO_DEG, pitch * RAD_TO_DEG, yaw * RAD_TO_DEG];
}
