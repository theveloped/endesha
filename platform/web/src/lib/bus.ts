// Thin zenoh-ts session wrapper: connect, latest-wins subscriptions,
// single-reply queries, liveliness watch.
import {
  CongestionControl,
  Config,
  Duration,
  KeyExpr,
  type Query,
  type Queryable,
  type LivelinessToken,
  type Publisher,
  RingChannel,
  Sample,
  SampleKind,
  Session,
} from "@eclipse-zenoh/zenoh-ts";
import { decodeBytes, decodeSample, encode } from "./codec";
import { REPLAY_ALIVE_GLOB } from "./config";

export type Unsubscribe = () => void;

export function connect(url: string): Promise<Session> {
  return Session.open(new Config(url));
}

/**
 * Subscribe with ring-buffer backpressure (capacity 1 = latest-wins for the
 * 200 Hz joints stream; use a larger capacity for io/status).
 */
export async function subscribeLatest(
  session: Session,
  key: string,
  onMsg: (msg: unknown, sample: Sample) => void,
  capacity = 1,
): Promise<Unsubscribe> {
  const sub = await session.declareSubscriber(new KeyExpr(key), {
    handler: new RingChannel<Sample>(capacity),
  });
  const receiver = sub.receiver();
  if (receiver !== undefined) {
    void (async () => {
      for await (const sample of receiver) {
        try {
          onMsg(decodeSample(sample), sample);
        } catch (e) {
          console.error(`decode failed on ${key}:`, e);
        }
      }
    })();
  }
  return () => void sub.undeclare();
}

/**
 * Follow a retained key (pub latest-wins + queryable answering the same
 * payload) with correct seed ordering: subscribe FIRST, then seed with a
 * query — deltas win over the seed (wire-contract RFC §3.1). Mirrors
 * wf/core/retained.py.
 */
export async function subscribeRetained(
  session: Session,
  key: string,
  onMsg: (msg: unknown) => void,
  capacity = 4,
): Promise<Unsubscribe> {
  let gotDelta = false;
  const unsubscribe = await subscribeLatest(
    session,
    key,
    (msg) => {
      gotDelta = true;
      onMsg(msg);
    },
    capacity,
  );
  void query(session, key, {}).then((seed) => {
    if (seed !== null && !gotDelta) onMsg(seed);
  });
  return unsubscribe;
}

/**
 * Like subscribeLatest but delivers the raw Sample — for binary payloads
 * (camera frames) whose payload is not CBOR.
 */
export async function subscribeRaw(
  session: Session,
  key: string,
  onSample: (sample: Sample) => void,
  capacity = 1,
): Promise<Unsubscribe> {
  const sub = await session.declareSubscriber(new KeyExpr(key), {
    handler: new RingChannel<Sample>(capacity),
  });
  const receiver = sub.receiver();
  if (receiver !== undefined) {
    void (async () => {
      for await (const sample of receiver) {
        try {
          onSample(sample);
        } catch (e) {
          console.error(`raw sample handler failed on ${key}:`, e);
        }
      }
    })();
  }
  return () => void sub.undeclare();
}

/** Issue a raw get and collect every successful Sample reply without decoding
 * its payload. Used by diagnostics where encoding, attachments, and raw bytes
 * are part of the data being inspected. */
export async function queryRawAll(
  session: Session,
  key: string,
  timeoutMs = 2000,
): Promise<Sample[]> {
  const receiver = await session.get(key, {
    timeout: Duration.milliseconds.of(timeoutMs),
  });
  const samples: Sample[] = [];
  if (receiver === undefined) return samples;
  for await (const reply of receiver) {
    const result = reply.result();
    if (result instanceof Sample) samples.push(result);
  }
  return samples;
}

/**
 * Issue a get, return the first Sample reply decoded; null on no reply
 * (timeout) or error-only replies.
 */
export async function query(
  session: Session,
  key: string,
  payload: unknown,
  timeoutMs = 5000,
): Promise<unknown | null> {
  const receiver = await session.get(key, {
    payload: encode(payload),
    timeout: Duration.milliseconds.of(timeoutMs),
  });
  if (receiver === undefined) return null;
  for await (const reply of receiver) {
    const result = reply.result();
    if (result instanceof Sample) return decodeSample(result);
  }
  return null;
}

/**
 * Issue a get and collect EVERY Sample reply (e.g. config/** globs served
 * one reply per matching key). Returns [] when no replies arrive.
 */
export async function queryAll(
  session: Session,
  key: string,
  payload?: unknown,
  timeoutMs = 5000,
): Promise<{ key: string; value: unknown }[]> {
  const timeout = Duration.milliseconds.of(timeoutMs);
  const receiver = await session.get(
    key,
    payload === undefined ? { timeout } : { payload: encode(payload), timeout },
  );
  const out: { key: string; value: unknown }[] = [];
  if (receiver === undefined) return out;
  for await (const reply of receiver) {
    const result = reply.result();
    if (result instanceof Sample)
      out.push({ key: result.keyexpr().toString(), value: decodeSample(result) });
  }
  return out;
}

/**
 * Live view of a realm-less config glob (e.g. `config/scene/**`): seed the
 * current entries with `queryAll`, then keep them current by applying
 * `subscribeLatest` deltas — the config service publishes each `cmd/set` value
 * (and an empty `{}` tombstone on `cmd/delete`) on its own key. An empty payload
 * removes the entry. `onChange` fires with the full `{name, value}[]` (name =
 * key with `stripPrefix` removed) on every update. Returns an unsubscribe.
 *
 * Subscribes BEFORE seeding so an edit landing mid-seed isn't missed; the seed
 * only fills keys a delta hasn't already set (deltas win over a staler seed).
 */
export async function subscribeConfigList(
  session: Session,
  glob: string,
  stripPrefix: string,
  onChange: (items: { name: string; value: unknown }[]) => void,
  capacity = 64,
): Promise<Unsubscribe> {
  const map = new Map<string, unknown>();
  const nameOf = (key: string) =>
    key.startsWith(stripPrefix) ? key.slice(stripPrefix.length) : key;
  const isTombstone = (v: unknown) =>
    v === null ||
    (typeof v === "object" && Object.keys(v as object).length === 0);
  const emit = () =>
    onChange([...map.entries()].map(([name, value]) => ({ name, value })));

  const unsub = await subscribeLatest(
    session,
    glob,
    (msg, sample) => {
      const name = nameOf(sample.keyexpr().toString());
      if (isTombstone(msg)) map.delete(name);
      else map.set(name, msg);
      emit();
    },
    capacity,
  );
  try {
    for (const { key, value } of await queryAll(session, glob)) {
      const name = nameOf(key);
      if (!map.has(name)) map.set(name, value);
    }
    emit();
  } catch (e) {
    console.error(`config seed failed for ${glob}:`, e);
  }
  return unsub;
}

/** A declared publisher: CBOR-encoding `put` plus `undeclare`. */
export interface BusPublisher {
  put: (msg: unknown) => void;
  undeclare: Unsubscribe;
}

/**
 * Declare a long-lived publisher and return a CBOR-encoding `put` plus an
 * `undeclare`. Used for the hold-to-jog stream: declare once on pointer-down,
 * `put` a JogCommand at 15 Hz, `undeclare` on pointer-up (the driver's 250 ms
 * watchdog halts the arm once the stream stops).
 */
export async function declarePublisher(
  session: Session,
  key: string,
): Promise<BusPublisher> {
  const pub = await session.declarePublisher(new KeyExpr(key));
  return {
    put: (msg: unknown) => void pub.put(encode(msg)),
    undeclare: () => void pub.undeclare(),
  };
}

// ── server side (the TS HAL serves contracts, not just consumes them) ──────

/** A frame publisher: `put` raw payload bytes with a CBOR attachment. Used by
 *  the camera2d image topic (payload = JPEG bytes, attachment = FrameHeader)
 *  and the status topic (payload = CBOR status, no attachment). Declared with
 *  CongestionControl.DROP so frames drop under backpressure rather than block —
 *  best-effort stream semantics (design §3), matching the Python HAL. */
export interface RawPublisher {
  put: (payload: Uint8Array, attachment?: Uint8Array) => void;
  undeclare: Unsubscribe;
}

export async function declareRawPublisher(
  session: Session,
  key: string,
  drop = true,
): Promise<RawPublisher> {
  const pub: Publisher = await session.declarePublisher(new KeyExpr(key), {
    congestionControl: drop ? CongestionControl.DROP : CongestionControl.BLOCK,
  });
  return {
    put: (payload: Uint8Array, attachment?: Uint8Array) =>
      void pub.put(payload, attachment === undefined ? undefined : { attachment }),
    undeclare: () => void pub.undeclare(),
  };
}

/** Decode a query's CBOR payload, or `{}` when absent (matches the Python
 *  `decode(query.payload) if query.payload is not None else {}` pattern). */
export function queryPayload(query: Query): unknown {
  const p = query.payload();
  return p === undefined ? {} : decodeBytes(p.toBytes());
}

/** Declare a queryable. The handler receives each Query; it MUST resolve, and
 *  the wrapper ALWAYS calls `query.finalize()` afterwards — without finalize the
 *  Python `session.get()` querier blocks until timeout. Reply with
 *  `replyBytes(query, key, bytes)`. */
export async function declareQueryable(
  session: Session,
  key: string,
  onQuery: (query: Query) => Promise<void>,
): Promise<Unsubscribe> {
  const queryable: Queryable = await session.declareQueryable(new KeyExpr(key), {
    complete: true,
    handler: (query: Query) => {
      void (async () => {
        try {
          await onQuery(query);
        } catch (e) {
          console.error(`queryable handler failed on ${key}:`, e);
        } finally {
          await query.finalize();
        }
      })();
    },
  });
  return () => void queryable.undeclare();
}

/** Reply to a query with raw CBOR bytes on the query's own key expression. */
export function replyBytes(query: Query, payload: Uint8Array): Promise<void> {
  return query.reply(query.keyExpr(), payload);
}

/** Assert a liveliness token; the token is held until `undeclare` (or session
 *  close), at which point watchers see the DELETE. Serves `.../alive`. */
export async function declareLivelinessToken(
  session: Session,
  key: string,
): Promise<Unsubscribe> {
  const token: LivelinessToken = await session.liveliness().declareToken(new KeyExpr(key));
  return () => void token.undeclare();
}

/**
 * Watch a liveliness token: PUT -> alive, DELETE -> down. `history: true`
 * delivers the current token state at declaration time.
 */
export async function watchAlive(
  session: Session,
  key: string,
  onChange: (alive: boolean) => void,
): Promise<Unsubscribe> {
  const sub = await session.liveliness().declareSubscriber(new KeyExpr(key), {
    history: true,
    handler: (sample: Sample) => {
      if (sample.kind() === SampleKind.PUT) onChange(true);
      else if (sample.kind() === SampleKind.DELETE) onChange(false);
    },
  });
  return () => void sub.undeclare();
}

/** Watch replay/{sid}/{contract}/{rid}/alive tokens; reports the live session-id set. */
export async function watchReplaySessions(
  session: Session,
  onChange: (sids: string[]) => void,
): Promise<Unsubscribe> {
  const tokens = new Map<string, Set<string>>(); // sid -> alive token keys
  const emit = () => onChange([...tokens.keys()].sort());
  const sub = await session
    .liveliness()
    .declareSubscriber(new KeyExpr(REPLAY_ALIVE_GLOB), {
      history: true,
      handler: (sample: Sample) => {
        const key = sample.keyexpr().toString();
        const sid = key.split("/")[1];
        if (sid === undefined) return;
        if (sample.kind() === SampleKind.PUT) {
          if (!tokens.has(sid)) tokens.set(sid, new Set());
          tokens.get(sid)!.add(key);
        } else if (sample.kind() === SampleKind.DELETE) {
          const set = tokens.get(sid);
          if (set === undefined) return;
          set.delete(key);
          if (set.size === 0) tokens.delete(sid);
        }
        emit();
      },
    });
  return () => void sub.undeclare();
}
