// The wire-contract reply envelope — mirrors wf/core/envelope.py
// (wire-contract RFC §4–§5).
//
// Every queryable request is {req_id, client_id?, args}; every reply is one
// tagged union: {ok:true, value} | {ok:true, goal} | {ok:false, error}.
// `call()` is branch-agnostic: it returns the value, transparently follows
// a goal to its retained result (which is recursively the envelope), and
// throws EnvelopeError otherwise — so an operation can move from sync to
// goal-shaped without breaking a single caller.
import { Session } from "@eclipse-zenoh/zenoh-ts";
import { v7 as uuidv7 } from "uuid";
import { query, subscribeLatest } from "./bus";

/** Closed error-code enum (RFC §5); additions are ADR-level events. */
export const CODES = [
  "invalid",
  "conflict",
  "busy",
  "unavailable",
  "not_found",
  "cancelled",
  "safety",
  "internal",
] as const;
export type ErrorCode = (typeof CODES)[number];

export interface WireError {
  code: ErrorCode;
  reason: string;
  detail?: string;
  retryable?: boolean;
}

export interface GoalInfo {
  goal_id: string;
  state: string;
  feedback_key: string;
  result_key: string;
  cancel_key: string;
  result_ttl_s: number;
}

export interface Envelope {
  ok: boolean;
  value?: Record<string, unknown>;
  goal?: GoalInfo;
  error?: WireError;
}

export class EnvelopeError extends Error {
  readonly error: WireError;

  constructor(error: WireError) {
    super(
      error.detail === undefined
        ? `${error.code}:${error.reason}`
        : `${error.code}:${error.reason}:${error.detail}`,
    );
    this.name = "EnvelopeError";
    this.error = error;
  }

  get code(): ErrorCode {
    return this.error.code;
  }

  get reason(): string {
    return this.error.reason;
  }

  get retryable(): boolean {
    return this.error.retryable === true;
  }
}

export function newReqId(): string {
  return uuidv7();
}

function asEnvelope(reply: unknown, key: string): Envelope {
  if (reply === null) {
    return {
      ok: false,
      error: { code: "unavailable", reason: "no_reply", detail: key, retryable: true },
    };
  }
  if (typeof reply !== "object" || !("ok" in (reply as Record<string, unknown>))) {
    return { ok: false, error: { code: "internal", reason: "bad_envelope" } };
  }
  return reply as Envelope;
}

export interface RequestOptions {
  clientId?: string;
  reqId?: string;
  timeoutMs?: number;
  /** goal-follow budget; only relevant when the reply is the goal branch */
  resultTimeoutMs?: number;
}

/** One enveloped query; absence (no reply) is `unavailable:no_reply`. */
export async function request(
  session: Session,
  key: string,
  args: Record<string, unknown>,
  opts: RequestOptions = {},
): Promise<Envelope> {
  const wire: Record<string, unknown> = { req_id: opts.reqId ?? newReqId(), args };
  if (opts.clientId !== undefined) wire.client_id = opts.clientId;
  const reply = await query(session, key, wire, opts.timeoutMs ?? 5000);
  return asEnvelope(reply, key);
}

/** Branch-agnostic call: value now, or follow the goal, or throw. */
export async function call(
  session: Session,
  key: string,
  args: Record<string, unknown>,
  opts: RequestOptions = {},
): Promise<Record<string, unknown>> {
  const reply = await request(session, key, args, opts);
  if (reply.ok && reply.goal !== undefined) {
    return follow(session, reply.goal, opts.resultTimeoutMs ?? 300_000);
  }
  if (reply.ok) return reply.value ?? {};
  throw new EnvelopeError(reply.error ?? { code: "internal", reason: "bad_envelope" });
}

/** Wait for an accepted goal's retained result: subscribe first, seed with
 * a query second — deltas win over the seed (RFC §3.1 discipline). */
async function follow(
  session: Session,
  goal: GoalInfo,
  resultTimeoutMs: number,
): Promise<Record<string, unknown>> {
  let settle: (wire: unknown) => void;
  const outcome = new Promise<unknown>((resolve) => {
    settle = resolve;
  });
  let done = false;
  const deliver = (wire: unknown) => {
    if (!done && typeof wire === "object" && wire !== null && "ok" in wire) {
      done = true;
      settle(wire);
    }
  };
  const unsubscribe = await subscribeLatest(session, goal.result_key, deliver, 1);
  try {
    void query(session, goal.result_key, {}).then((seed) => deliver(seed));
    const timeout = new Promise<never>((_, reject) => {
      setTimeout(
        () =>
          reject(
            new EnvelopeError({
              code: "unavailable",
              reason: "result_timeout",
              detail: goal.goal_id,
              retryable: true,
            }),
          ),
        resultTimeoutMs,
      );
    });
    const wire = (await Promise.race([outcome, timeout])) as Envelope;
    if (wire.ok) return wire.value ?? {};
    throw new EnvelopeError(wire.error ?? { code: "internal", reason: "bad_envelope" });
  } finally {
    unsubscribe();
  }
}
