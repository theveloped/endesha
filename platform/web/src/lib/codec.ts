// CBOR codec over zenoh payloads (wire format matches wf.core.codec).
import { decode, encode } from "cbor-x";
import type { Sample } from "@eclipse-zenoh/zenoh-ts";

export { encode };

export function decodeSample(sample: Sample): unknown {
  return decode(sample.payload().toBytes());
}
