// Minimal action client mirroring the wire protocol in wf/core/action.py
// (design Appendix A): feedback + result subscribers are declared BEFORE
// the goal query so early samples are not lost; the result sample resolves
// the handle and undeclares both subscribers.
import { KeyExpr, Sample, Session } from "@eclipse-zenoh/zenoh-ts";
import { v7 as uuidv7 } from "uuid";
import { query } from "./bus";
import { call } from "./envelope";
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
  Ack,
  ProgramSaveReply,
  ProgramSourceReply,
  CancelReply,
  GoalFeedback,
  GoalReply,
  GoalResult,
  Recipe,
  RecipeReply,
  SetSourceReply,
  Waypoint,
} from "./messages";

export interface GoalHandle {
  goalId: string;
  /** Resolves with the terminal result published on {prefix}/{goal_id}/result. */
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
  return sendGoal(session, actionPrefix(realm), "execute_path", { waypoints, client_id: clientId ?? null }, { onFeedback });
}

/** Submit a goal to `{prefix}/{name}` and return a handle whose `result`
 * resolves with the terminal result (any action server, any contract). */
export async function sendGoal(
  session: Session,
  prefix: string,
  name: string,
  goal: Record<string, unknown>,
  { onFeedback }: { onFeedback?: (fb: GoalFeedback) => void } = {},
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
          resolveResult(decodeSample(sample) as GoalResult);
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

  let reply: GoalReply | null;
  try {
    reply = (await query(session, `${prefix}/${name}`, { goal_id: goalId, goal })) as GoalReply | null;
  } catch (e) {
    undeclareBoth();
    throw e;
  }
  if (reply === null) {
    undeclareBoth();
    throw new Error(`no reply from action server for ${name}`);
  }
  if (!reply.accepted) {
    undeclareBoth();
    throw new Error(reply.reason ?? "rejected");
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
  const reply = await query(session, `${prefix}/cancel`, { goal_id: goalId });
  if (reply === null) throw new Error(`no cancel reply for goal ${goalId}`);
  return reply as CancelReply;
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
  return sendGoal(session, washerActionPrefix(realm, rid), name, { client_id: clientId, ...goal });
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
): Promise<Ack> {
  const reply = await query(session, cmdSetDo(realm), {
    bank: "standard",
    pin,
    value,
  });
  if (reply === null) throw new Error("no reply from cmd/set_do");
  return reply as Ack;
}

export async function stop(session: Session, realm: string): Promise<Ack> {
  const reply = await query(session, cmdStop(realm), {});
  if (reply === null) throw new Error("no reply from cmd/stop");
  return reply as Ack;
}

export async function clearProtectiveStop(
  session: Session,
  realm: string,
): Promise<Ack> {
  const reply = await query(session, cmdClearProtectiveStop(realm), {});
  if (reply === null)
    throw new Error("no reply from cmd/clear_protective_stop");
  return reply as Ack;
}

export async function setTcp(
  session: Session,
  realm: string,
  name: string,
): Promise<Ack> {
  const reply = await query(session, cmdSetTcp(realm), { name });
  if (reply === null) throw new Error("no reply from cmd/set_tcp");
  return reply as Ack;
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

export interface ConfigSetReply {
  ok: boolean;
  revision: number | null;
  error: string | null;
}

export async function configSet(
  session: Session,
  key: string,
  value: unknown,
): Promise<ConfigSetReply> {
  const reply = await query(session, configCmdSet(), { key, value });
  if (reply === null)
    throw new Error("no reply from config/cmd/set (config service running?)");
  return reply as ConfigSetReply;
}

export interface ConfigDeleteReply {
  ok: boolean;
  error: string | null;
}

export async function configDelete(
  session: Session,
  key: string,
): Promise<ConfigDeleteReply> {
  const reply = await query(session, configCmdDelete(), { key });
  if (reply === null)
    throw new Error("no reply from config/cmd/delete (config service running?)");
  return reply as ConfigDeleteReply;
}


/** Cold-switch a device's source mode (live/sim/replay/off) via the supervisor. */
export async function setDeviceSource(
  session: Session,
  realm: string,
  deviceId: string,
  source: string,
): Promise<SetSourceReply> {
  const reply = await query(session, supervisorCmdSetSource(realm), {
    device_id: deviceId,
    source,
  });
  if (reply === null)
    throw new Error("no reply from supervisor cmd/set_source (supervisor running?)");
  return reply as SetSourceReply;
}
