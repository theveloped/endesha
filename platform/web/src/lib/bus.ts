// Thin zenoh-ts session wrapper: connect, latest-wins subscriptions,
// single-reply queries, liveliness watch.
import {
  Config,
  Duration,
  KeyExpr,
  RingChannel,
  Sample,
  SampleKind,
  Session,
} from "@eclipse-zenoh/zenoh-ts";
import { decodeSample, encode } from "./codec";
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

/**
 * Watch `{realm}/task/{flow}/alive` liveliness for one realm; reports the
 * set of currently-running flow names (sorted). Mirrors watchReplaySessions
 * — a flow appears only while its task_runner process holds the token.
 */
export async function watchTaskFlows(
  session: Session,
  realm: string,
  onChange: (flows: string[]) => void,
): Promise<Unsubscribe> {
  const live = new Set<string>();
  const emit = () => onChange([...live].sort());
  const sub = await session
    .liveliness()
    .declareSubscriber(new KeyExpr(`${realm}/task/*/alive`), {
      history: true,
      handler: (sample: Sample) => {
        // key = {realm}/task/{flow}/alive
        const flow = sample.keyexpr().toString().split("/").at(-2);
        if (flow === undefined) return;
        if (sample.kind() === SampleKind.PUT) live.add(flow);
        else if (sample.kind() === SampleKind.DELETE) live.delete(flow);
        emit();
      },
    });
  return () => void sub.undeclare();
}
