// Minimal action client mirroring the wire protocol in wf/core/action.py
// (design Appendix A): feedback + result subscribers are declared BEFORE
// the goal query so early samples are not lost; the result sample resolves
// the handle and undeclares both subscribers.
import { KeyExpr, Sample, Session } from "@eclipse-zenoh/zenoh-ts";
import { v7 as uuidv7 } from "uuid";
import { query } from "./bus";
import { call, EnvelopeError, type Envelope } from "./envelope";
import { decodeSample } from "./codec";
import {
  actionPrefix,
  controlCmdAcquire,
  dioCmdForce,
  dioCmdSet,
  programCmd,
  programCmdEvent,
  programsCmdDelete,
  programsCmdLoad,
  programsCmdSave,
  programsCmdSource,
  tagsCmdForce,
  tagsCmdWrite,
  washerActionPrefix,
  washerCmdGetRecipe,
  washerCmdSetRecipe,
  washerCmdStopDoor,
  type UnitCommand,
  cmdClearProtectiveStop,
  controlCmdRelease,
  cmdSetDo,
  cmdSetTcp,
  cmdStop,
  configCmdDelete,
  configCmdSet,
  supervisorCmdSetSource,
} from "./config";
import type {
  ProgramSaveReply,
  ProgramSourceReply,
  CancelReply,
  GoalFeedback,
  GoalResult,
  Recipe,
  RecipeReply,
  SetSourceReply,
  Waypoint,
} from "./messages";

export interface GoalHandle {
  goalId: string;
  /** Resolves with the parsed terminal result envelope from
   * {prefix}/{goal_id}/result. */
  result: Promise<GoalResult>;
}

export async function sendExecutePath(
  session: Session,
  realm: string,
  waypoints: Waypoint[],
  {
    onFeedback,
    clientId,
  }: { onFeedback?: (fb: GoalFeedback) => void; clientId?: string } = {},
): Promise<GoalHandle> {
  return sendGoal(session, actionPrefix(realm), "execute_path", { waypoints }, { onFeedback, clientId });
}

/** Submit an envelope goal to `{prefix}/{name}` and return a handle whose
 * `result` resolves with the terminal result envelope (any action server,
 * any contract). Throws EnvelopeError on rejection. The goal id is the
 * request's req_id, so the subscribers can be declared BEFORE the query —
 * early samples are not lost. */
export async function sendGoal(
  session: Session,
  prefix: string,
  name: string,
  goal: Record<string, unknown>,
  { onFeedback, clientId }: { onFeedback?: (fb: GoalFeedback) => void; clientId?: string } = {},
): Promise<GoalHandle> {
  const goalId = uuidv7();

  const feedbackSub = await session.declareSubscriber(
    new KeyExpr(`${prefix}/${goalId}/feedback`),
    {
      handler: (sample: Sample) => {
        if (onFeedback === undefined) return;
        try {
          onFeedback(decodeSample(sample) as GoalFeedback);
        } catch (e) {
          console.error("feedback decode failed:", e);
        }
      },
    },
  );

  let resolveResult!: (result: GoalResult) => void;
  const result = new Promise<GoalResult>((resolve) => {
    resolveResult = resolve;
  });
  const resultSub = await session.declareSubscriber(
    new KeyExpr(`${prefix}/${goalId}/result`),
    {
      handler: (sample: Sample) => {
        try {
          const wire = decodeSample(sample) as Envelope;
          resolveResult({
            ok: wire.ok,
            value: wire.value ?? {},
            error: wire.error ?? null,
          });
        } catch (e) {
          console.error("result decode failed:", e);
        }
      },
    },
  );
  const undeclareBoth = () => {
    void feedbackSub.undeclare();
    void resultSub.undeclare();
  };
  void result.then(undeclareBoth);

  let reply: Envelope;
  try {
    const wire: Record<string, unknown> = { req_id: goalId, args: goal };
    if (clientId !== undefined) wire.client_id = clientId;
    const raw = await query(session, `${prefix}/${name}`, wire);
    if (raw === null) throw new Error(`no reply from action server for ${name}`);
    reply = raw as Envelope;
  } catch (e) {
    undeclareBoth();
    throw e;
  }
  if (!reply.ok || reply.goal === undefined) {
    undeclareBoth();
    throw new EnvelopeError(reply.error ?? { code: "internal", reason: "bad_envelope" });
  }
  return { goalId, result };
}

export async function cancelGoal(
  session: Session,
  realm: string,
  goalId: string,
): Promise<CancelReply> {
  return cancelGoalAt(session, actionPrefix(realm), goalId);
}

export async function cancelGoalAt(session: Session, prefix: string, goalId: string): Promise<CancelReply> {
  return (await call(session, `${prefix}/cancel`, { goal_id: goalId })) as unknown as CancelReply;
}

// ── washer ──────────────────────────────────────────────────────────────────

export type WasherAction = "open_door" | "close_door" | "start_wash" | "reset";

export async function washerAction(
  session: Session,
  realm: string,
  rid: string,
  clientId: string,
  name: WasherAction,
  goal: Record<string, unknown> = {},
): Promise<GoalHandle> {
  return sendGoal(session, washerActionPrefix(realm, rid), name, goal, { clientId });
}

export async function washerCancel(session: Session, realm: string, rid: string, goalId: string): Promise<CancelReply> {
  return cancelGoalAt(session, washerActionPrefix(realm, rid), goalId);
}

// Washer commands speak the envelope: resolve on success, throw EnvelopeError.
export async function washerStopDoor(session: Session, realm: string, rid: string, clientId: string): Promise<void> {
  await call(session, washerCmdStopDoor(realm, rid), {}, { clientId });
}

export async function washerGetRecipe(session: Session, realm: string, rid: string): Promise<RecipeReply> {
  return (await call(session, washerCmdGetRecipe(realm, rid), {})) as unknown as RecipeReply;
}

export async function washerSetRecipe(
  session: Session,
  realm: string,
  rid: string,
  clientId: string,
  recipe: Recipe,
): Promise<void> {
  await call(session, washerCmdSetRecipe(realm, rid), { recipe }, { clientId, timeoutMs: 15000 });
}

export async function setDo(
  session: Session,
  realm: string,
  pin: number,
  value: boolean,
): Promise<void> {
  await call(session, cmdSetDo(realm), { bank: "standard", pin, value });
}

export async function stop(session: Session, realm: string): Promise<void> {
  await call(session, cmdStop(realm), {});
}

export async function clearProtectiveStop(
  session: Session,
  realm: string,
): Promise<void> {
  await call(session, cmdClearProtectiveStop(realm), {});
}

export async function setTcp(
  session: Session,
  realm: string,
  name: string,
): Promise<void> {
  await call(session, cmdSetTcp(realm), { name });
}

// dio/tags commands speak the wire-contract envelope (lib/envelope.ts):
// they resolve on success and throw EnvelopeError ("code:reason[:detail]").
export async function dioSet(
  session: Session,
  realm: string,
  rid: string,
  clientId: string,
  channel: string,
  value: boolean | number,
): Promise<void> {
  await call(session, dioCmdSet(realm, rid), { channel, value }, { clientId });
}

/** ``value: null`` clears the force. */
export async function dioForce(
  session: Session,
  realm: string,
  rid: string,
  clientId: string,
  channel: string,
  value: boolean | number | null,
): Promise<void> {
  await call(session, dioCmdForce(realm, rid), { channel, value }, { clientId });
}

export async function tagsWrite(
  session: Session,
  realm: string,
  rid: string,
  clientId: string,
  tag: string,
  value: boolean | number | string,
): Promise<void> {
  await call(session, tagsCmdWrite(realm, rid), { tag, value }, { clientId });
}

/** ``value: null`` clears the force. */
export async function tagsForce(
  session: Session,
  realm: string,
  rid: string,
  clientId: string,
  tag: string,
  value: boolean | number | string | null,
): Promise<void> {
  await call(session, tagsCmdForce(realm, rid), { tag, value }, { clientId });
}

// Program runner commands speak the envelope: resolve on success, throw
// EnvelopeError ("code:reason[:detail]") otherwise.
export async function programLoad(
  session: Session,
  realm: string,
  name: string,
  bindings: Record<string, string>,
  params: Record<string, unknown>,
): Promise<void> {
  await call(session, programsCmdLoad(realm), { name, bindings, params });
}

export async function programCommand(
  session: Session,
  realm: string,
  command: UnitCommand,
  reason?: string,
): Promise<void> {
  await call(session, programCmd(realm, command), reason ? { reason } : {});
}

export async function programSource(
  session: Session,
  realm: string,
  nameOrFile: { name: string } | { file: string },
): Promise<ProgramSourceReply> {
  return (await call(session, programsCmdSource(realm), nameOrFile)) as unknown as ProgramSourceReply;
}

export async function programSave(
  session: Session,
  realm: string,
  file: string,
  text: string,
): Promise<ProgramSaveReply> {
  return (await call(session, programsCmdSave(realm), { file, text })) as unknown as ProgramSaveReply;
}

export async function programDeleteFile(session: Session, realm: string, name: string): Promise<void> {
  await call(session, programsCmdDelete(realm), { name });
}

export async function programEvent(
  session: Session,
  realm: string,
  event: string,
  data: Record<string, unknown> = {},
): Promise<void> {
  await call(session, programCmdEvent(realm), { event, data });
}

// Control lease: envelope queryables (holds/owner state comes from the
// retained state/owner key, not from these replies).
export async function acquireControl(
  session: Session,
  realm: string,
  clientId: string,
  user: string,
): Promise<void> {
  await call(session, controlCmdAcquire(realm), { user }, { clientId });
}

export async function releaseControl(
  session: Session,
  realm: string,
  clientId: string,
): Promise<void> {
  await call(session, controlCmdRelease(realm), {}, { clientId });
}

/** config/cmd/set envelope value. */
export interface ConfigSetReply {
  revision: number;
}

// Config writes speak the envelope: resolve on success, throw EnvelopeError.
export async function configSet(
  session: Session,
  key: string,
  value: unknown,
): Promise<ConfigSetReply> {
  return (await call(session, configCmdSet(), { key, value })) as unknown as ConfigSetReply;
}

export async function configDelete(session: Session, key: string): Promise<void> {
  await call(session, configCmdDelete(), { key });
}


/** Cold-switch a device's source mode (live/sim/replay/off) via the supervisor. */
export async function setDeviceSource(
  session: Session,
  realm: string,
  deviceId: string,
  source: string,
): Promise<SetSourceReply> {
  return (await call(session, supervisorCmdSetSource(realm), {
    device_id: deviceId,
    source,
  })) as unknown as SetSourceReply;
}
