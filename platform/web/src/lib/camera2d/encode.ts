// In-page JPEG encode for the serving path (the TS HAL runs in the browser, so
// there is no Node/sharp side). gl.readPixels gives bottom-up RGBA; we flip to
// top-down and encode with @jsquash/jpeg (mozjpeg compiled to WASM). The
// Phase-2 measurement showed OffscreenCanvas.convertToBlob is ~1.5 s under
// headless SwiftShader (unusable); mozjpeg-WASM encodes a stream-scale frame in
// single-digit ms, so the render rate (~15 Hz) stays the throughput ceiling.
//
// init() must run once before the first encode (loads the WASM). Encoding is
// done on the main thread for now: readback (~5 ms) + encode (~few ms) is far
// under the ~66 ms/frame budget at 15 Hz. If profiling later shows encode
// stealing render time, move encodeJpeg into a Worker with the RGBA buffer
// transferred — the signature is worker-friendly (plain bytes in, bytes out).
import encode, { init as initJpeg } from "@jsquash/jpeg/encode";

let ready: Promise<void> | null = null;

/** Load the mozjpeg WASM module once. Safe to call repeatedly. */
export function initEncoder(): Promise<void> {
  ready ??= initJpeg();
  return ready;
}

/** Flip RGBA rows in place: GL reads bottom-to-top (origin bottom-left), images
 *  are top-to-bottom. Swaps whole rows via a scratch row buffer. */
function flipRowsInPlace(rgba: Uint8Array, w: number, h: number): void {
  const stride = w * 4;
  const tmp = new Uint8Array(stride);
  for (let y = 0; y < h >> 1; y++) {
    const top = y * stride;
    const bot = (h - 1 - y) * stride;
    tmp.set(rgba.subarray(top, top + stride));
    rgba.copyWithin(top, bot, bot + stride);
    rgba.set(tmp, bot);
  }
}

/** Encode bottom-up RGBA pixels (gl.readPixels output) to JPEG bytes. `quality`
 *  is 1..100 (the contract's FrameSpec.quality). Flips vertically first. */
export async function encodeJpeg(
  rgba: Uint8Array,
  w: number,
  h: number,
  quality: number,
): Promise<Uint8Array> {
  await initEncoder();
  flipRowsInPlace(rgba, w, h);
  // ImageData needs a Uint8ClampedArray backed by a plain ArrayBuffer. A fresh
  // clamped array over the (already-flipped) bytes satisfies that and avoids
  // SharedArrayBuffer typing on rgba.buffer.
  const clamped = new Uint8ClampedArray(w * h * 4);
  clamped.set(rgba.subarray(0, w * h * 4));
  const data = new ImageData(clamped, w, h);
  const buf = await encode(data, { quality });
  return new Uint8Array(buf);
}
