// CBOR codec over zenoh payloads (wire format matches wf.core.codec).
import { decode, encode } from "cbor-x";
import type { Sample } from "@eclipse-zenoh/zenoh-ts";

export { encode };

/** Decode CBOR bytes (a ZBytes payload/attachment already converted to a
 *  Uint8Array). */
export function decodeBytes(bytes: Uint8Array): unknown {
  return decode(bytes);
}

export function decodeSample(sample: Sample): unknown {
  return decode(sample.payload().toBytes());
}
