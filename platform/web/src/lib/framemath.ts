// Pure frame-tree math over the static config frames (THREE-backed, no drei).
// Mirrors wf.core.frametree: chain parents to world, identity for ROOT or
// unknown/cyclic frames. Shared by the 3D overlays and the Operate jog page.
import * as THREE from "three";
import type { FrameDef } from "./messages";

export const ROOT = "world";
export const BASE_FRAME = "arm/r1/base";

/** Dynamic flange frame: scene objects posed in it are end-of-arm tools rigidly
 *  mounted on the flange (not static-world geometry). Recognised by the collision
 *  engine, the sim camera, and the twin's FlangeToolMeshes overlay. */
export const FLANGE_FRAME = "arm/r1/flange";

/** World is Z-up; three.js is Y-up. Every world-frame render group applies this
 *  -90° about X, mapping world (x, y, z) -> three (x, z, -y). The robot and
 *  base-frame overlays nest a base-frame matrix INSIDE this group. */
export const ZUP_TO_YUP: [number, number, number] = [-Math.PI / 2, 0, 0];

export function localMatrix(def: FrameDef): THREE.Matrix4 {
  return new THREE.Matrix4().compose(
    new THREE.Vector3(def.xyz[0], def.xyz[1], def.xyz[2]),
    new THREE.Quaternion(def.quat[0], def.quat[1], def.quat[2], def.quat[3]),
    new THREE.Vector3(1, 1, 1),
  );
}

/** T_world<-name by chaining parents; identity for ROOT or unknown/cyclic. */
export function frameWorldMatrix(
  frames: Map<string, FrameDef>,
  name: string,
): THREE.Matrix4 {
  const chain: FrameDef[] = [];
  const seen = new Set<string>();
  let cur = name;
  while (cur !== ROOT) {
    if (seen.has(cur)) return new THREE.Matrix4(); // cycle guard
    const def = frames.get(cur);
    if (def === undefined) return new THREE.Matrix4(); // unknown -> identity
    seen.add(cur);
    chain.push(def);
    cur = def.parent;
  }
  // world<-name = (world<-child) · … · (parent<-name): closest-to-world first.
  const m = new THREE.Matrix4();
  for (let i = chain.length - 1; i >= 0; i--) m.multiply(localMatrix(chain[i]));
  return m;
}

/**
 * Quaternion of a reference frame's axes expressed in the arm base
 * (R_base<-frame), the same `ref_R` the driver uses for jogging. Reserved
 * names: "base" -> identity; "tool" -> the live TCP axes (`tcpQuat`). Any
 * other name resolves from the static config frame chain.
 */
export function refRotationQuat(
  frames: Map<string, FrameDef>,
  frameName: string,
  tcpQuat: [number, number, number, number],
): THREE.Quaternion {
  if (frameName === "base") return new THREE.Quaternion();
  if (frameName === "tool")
    return new THREE.Quaternion(tcpQuat[0], tcpQuat[1], tcpQuat[2], tcpQuat[3]);
  const dummy = new THREE.Vector3();
  const qBase = new THREE.Quaternion();
  frameWorldMatrix(frames, BASE_FRAME).decompose(dummy, qBase, new THREE.Vector3());
  const qFrame = new THREE.Quaternion();
  frameWorldMatrix(frames, frameName).decompose(dummy, qFrame, new THREE.Vector3());
  // R_base<-frame = R_base<-world · R_world<-frame = qBase⁻¹ · qFrame
  return qBase.invert().multiply(qFrame);
}
