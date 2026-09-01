# Wire vocabulary

The conventions every wire payload follows (wire-contract RFC §6). These
were habits; this page makes them rules. Conformance suites and the
cross-language CBOR gate enforce them as contracts migrate.

## Encoding

- CBOR everywhere structured (`wf.core.codec` ↔ `web/src/lib/codec.ts`).
- Field numbers are typed: a field a contract declares `float` is encoded
  as a CBOR float even for whole values (`1.0` never becomes an int) —
  the camera2d write-side encoder and the CBOR gate exist for exactly
  this.
- **No anonymous payloads**: every `value`, stream sample, and retained
  payload is a named message type in the contract's `messages.py`, with
  symmetric `to_wire`/`from_wire`.

## Fields

- `t` — capture time, integer **nanoseconds**. Every stream/retained
  payload carries it.
- `seq` — monotonic per-publisher counter, **mandatory on stream samples**
  (streams only for now — RFC review decision §11.4).
- Units: SI bare; anything else suffixed (`_deg`, `_s`, `_ms`). Joints
  are radians; frames use `rpy_deg` — the suffix carries the difference.
- **Absent means "no statement"; `null` means "explicitly none"** (e.g.
  `ForceChannel.value: null` clears the force).
- Ids: `req_id` (client-minted UUIDv7 per request), `client_id` (who acts;
  the lease check reads it), `goal_id` (= the adopted `req_id`).

## Envelope (commands only)

Requests/replies of `cmd/*` and action queryables follow
[ADR-0013](decisions/0013-reply-envelope.md). Retained reads answer with
the identical published payload, unenveloped; streams carry no wrapper.
Error `code` comes from the closed 8-value enum in `wf.core.envelope`;
`reason` from the contract's registered `ERROR_REASONS`; `detail` is
human-oriented and never parsed.

## Evolution

- Tolerant reader: unknown fields are ignored, never an error.
- Changes are additive-only; a breaking change means a **new key**, not a
  mutated message. This keeps recorded MCAP files replayable against
  future code — for a record-everything platform that is a requirement,
  not hygiene.
