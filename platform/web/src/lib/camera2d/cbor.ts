// Minimal CBOR encoder for the camera2d contract wire messages, matching
// Python `wf.core.codec.encode` == cbor2.dumps(obj, canonical=False):
//   - definite-length maps (major 5) in INSERTION order (no key sorting),
//   - definite-length arrays (major 4) and byte strings (major 2),
//   - text strings (major 3, UTF-8),
//   - ints minimal-length (major 0/1), bool 0xF5/0xF4, null 0xF6,
//   - floats ALWAYS 8-byte IEEE-754 doubles (0xFB).
//
// We hand-roll rather than use cbor-x for ONE reason: cbor-x encodes an
// integral-valued JS number (1.0 === 1) as a CBOR int, but the contract
// declares fields like scale/rate_hz/exposure_us/gain_db/pose as floats, and a
// `cbor2`-decoding Python consumer must see a float there. JS has no float/int
// distinction, so the caller marks floats with `f(x)` (-> Flt) and arrays of
// floats with `farr(xs)`; everything else follows JS types. cbor-x stays the
// DECODER on the read path (it is lenient about int-vs-float); this encoder is
// the WRITE path only.
//
// The message set is tiny and fixed, so a focused serializer is simpler and
// more correct here than bending a general library. Decode-only conformance
// would tolerate int-for-float, but other Python consumers (genicam parity,
// recorder) want true floats — so we emit them.

/** Wrapper marking a number that MUST serialize as a CBOR float64. */
export class Flt {
  readonly value: number;
  constructor(value: number) {
    this.value = value;
  }
}

/** Mark a number as a CBOR float64. */
export function f(x: number): Flt {
  return new Flt(x);
}

/** Mark an array of numbers as CBOR float64 elements (pose xyz/quat). */
export function farr(xs: number[]): Flt[] {
  return xs.map((x) => new Flt(x));
}

export type Wire =
  | number
  | bigint
  | boolean
  | string
  | null
  | undefined
  | Uint8Array
  | Flt
  | Wire[]
  | { [k: string]: Wire };

class Buf {
  private bytes: number[] = [];
  push(...b: number[]): void {
    for (const x of b) this.bytes.push(x & 0xff);
  }
  pushAll(b: Uint8Array): void {
    for (const x of b) this.bytes.push(x);
  }
  toBytes(): Uint8Array {
    return Uint8Array.from(this.bytes);
  }
}

// Major-type header: type in the top 3 bits, `n` as the argument with
// minimal-length encoding (RFC 8949 baseline, same as cbor2).
function header(out: Buf, major: number, n: number | bigint): void {
  const mt = major << 5;
  const v = typeof n === "bigint" ? n : Math.trunc(n);
  if (v < 0) throw new Error(`header arg must be non-negative, got ${v}`);
  if (v < 24) {
    out.push(mt | Number(v));
  } else if (v < 0x100) {
    out.push(mt | 24, Number(v));
  } else if (v < 0x10000) {
    const x = Number(v);
    out.push(mt | 25, (x >> 8) & 0xff, x & 0xff);
  } else if (v < 0x100000000) {
    const x = Number(v);
    out.push(mt | 26, (x >>> 24) & 0xff, (x >> 16) & 0xff, (x >> 8) & 0xff, x & 0xff);
  } else {
    // 8-byte argument (e.g. t_capture/seq nanoseconds beyond 2^32).
    let b = typeof n === "bigint" ? n : BigInt(Math.trunc(n));
    const out8 = new Uint8Array(8);
    for (let i = 7; i >= 0; i--) {
      out8[i] = Number(b & 0xffn);
      b >>= 8n;
    }
    out.push(mt | 27);
    out.pushAll(out8);
  }
}

const TEXT = new TextEncoder();

function encodeValue(out: Buf, v: Wire): void {
  if (v === null || v === undefined) {
    out.push(0xf6); // null
    return;
  }
  if (v instanceof Flt) {
    out.push(0xfb);
    const dv = new DataView(new ArrayBuffer(8));
    dv.setFloat64(0, v.value, false); // big-endian
    for (let i = 0; i < 8; i++) out.push(dv.getUint8(i));
    return;
  }
  if (typeof v === "boolean") {
    out.push(v ? 0xf5 : 0xf4);
    return;
  }
  if (typeof v === "bigint") {
    if (v < 0n) {
      header(out, 1, -1n - v); // negative int (major 1)
    } else {
      header(out, 0, v); // unsigned int (major 0)
    }
    return;
  }
  if (typeof v === "number") {
    if (Number.isInteger(v)) {
      if (v < 0) header(out, 1, -1 - v);
      else header(out, 0, v);
    } else {
      // Non-integral JS number -> float64 (cbor2 emits doubles too).
      out.push(0xfb);
      const dv = new DataView(new ArrayBuffer(8));
      dv.setFloat64(0, v, false);
      for (let i = 0; i < 8; i++) out.push(dv.getUint8(i));
    }
    return;
  }
  if (typeof v === "string") {
    const b = TEXT.encode(v);
    header(out, 3, b.length);
    out.pushAll(b);
    return;
  }
  if (v instanceof Uint8Array) {
    header(out, 2, v.length); // byte string (major 2)
    out.pushAll(v);
    return;
  }
  if (Array.isArray(v)) {
    header(out, 4, v.length);
    for (const e of v) encodeValue(out, e);
    return;
  }
  // plain object -> map (major 5), keys in insertion order.
  const keys = Object.keys(v);
  header(out, 5, keys.length);
  for (const k of keys) {
    encodeValue(out, k);
    encodeValue(out, v[k]);
  }
}

/** Encode a wire object to CBOR bytes matching Python cbor2(canonical=False). */
export function encodeWire(obj: Wire): Uint8Array {
  const out = new Buf();
  encodeValue(out, obj);
  return out.toBytes();
}
