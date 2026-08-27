// Minimal action client mirroring the wire protocol in wf/core/action.py
// (design Appendix A): feedback + result subscribers are declared BEFORE
// the goal query so early samples are not lost; the result sample resolves
// the handle and undeclares both subscribers.
import { KeyExpr, Sample, Session } from "@eclipse-zenoh/zenoh-ts";
import { v7 as uuidv7 } from "uuid";
import { query } from "./bus";
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
  ControlAck,
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

export async function washerStopDoor(session: Session, realm: string, rid: string, clientId: string): Promise<Ack> {
  const reply = await query(session, washerCmdStopDoor(realm, rid), { client_id: clientId });
  if (reply === null) throw new Error("no reply from washer cmd/stop_door");
  return reply as Ack;
}

export async function washerGetRecipe(session: Session, realm: string, rid: string): Promise<RecipeReply> {
  const reply = await query(session, washerCmdGetRecipe(realm, rid), {});
  if (reply === null) throw new Error("no reply from washer cmd/get_recipe");
  return reply as RecipeReply;
}

export async function washerSetRecipe(
  session: Session,
  realm: string,
  rid: string,
  clientId: string,
  recipe: Recipe,
): Promise<Ack> {
  const reply = await query(session, washerCmdSetRecipe(realm, rid), { client_id: clientId, recipe }, 15000);
  if (reply === null) throw new Error("no reply from washer cmd/set_recipe");
  return reply as Ack;
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

export async function dioSet(
  session: Session,
  realm: string,
  rid: string,
  clientId: string,
  channel: string,
  value: boolean | number,
): Promise<Ack> {
  const reply = await query(session, dioCmdSet(realm, rid), {
    client_id: clientId,
    channel,
    value,
  });
  if (reply === null) throw new Error("no reply from dio cmd/set");
  return reply as Ack;
}

/** ``value: null`` clears the force. */
export async function dioForce(
  session: Session,
  realm: string,
  rid: string,
  clientId: string,
  channel: string,
  value: boolean | number | null,
): Promise<Ack> {
  const reply = await query(session, dioCmdForce(realm, rid), {
    client_id: clientId,
    channel,
    value,
  });
  if (reply === null) throw new Error("no reply from dio cmd/force");
  return reply as Ack;
}

export async function tagsWrite(
  session: Session,
  realm: string,
  rid: string,
  clientId: string,
  tag: string,
  value: boolean | number | string,
): Promise<Ack> {
  const reply = await query(session, tagsCmdWrite(realm, rid), { client_id: clientId, tag, value });
  if (reply === null) throw new Error("no reply from tags cmd/write");
  return reply as Ack;
}

/** ``value: null`` clears the force. */
export async function tagsForce(
  session: Session,
  realm: string,
  rid: string,
  clientId: string,
  tag: string,
  value: boolean | number | string | null,
): Promise<Ack> {
  const reply = await query(session, tagsCmdForce(realm, rid), { client_id: clientId, tag, value });
  if (reply === null) throw new Error("no reply from tags cmd/force");
  return reply as Ack;
}

export async function programLoad(
  session: Session,
  realm: string,
  name: string,
  bindings: Record<string, string>,
  params: Record<string, unknown>,
): Promise<Ack> {
  const reply = await query(session, programsCmdLoad(realm), { name, bindings, params });
  if (reply === null) throw new Error("no reply from programs/cmd/load");
  return reply as Ack;
}

export async function programCommand(
  session: Session,
  realm: string,
  command: UnitCommand,
  reason?: string,
): Promise<Ack> {
  const reply = await query(session, programCmd(realm, command), reason ? { reason } : {});
  if (reply === null) throw new Error(`no reply from program/cmd/${command}`);
  return reply as Ack;
}

export async function programSource(
  session: Session,
  realm: string,
  nameOrFile: { name: string } | { file: string },
): Promise<ProgramSourceReply> {
  const reply = await query(session, programsCmdSource(realm), nameOrFile);
  if (reply === null) throw new Error("no reply from programs/cmd/source");
  return reply as ProgramSourceReply;
}

export async function programSave(
  session: Session,
  realm: string,
  file: string,
  text: string,
): Promise<ProgramSaveReply> {
  const reply = await query(session, programsCmdSave(realm), { file, text });
  if (reply === null) throw new Error("no reply from programs/cmd/save");
  return reply as ProgramSaveReply;
}

export async function programDeleteFile(session: Session, realm: string, name: string): Promise<Ack> {
  const reply = await query(session, programsCmdDelete(realm), { name });
  if (reply === null) throw new Error("no reply from programs/cmd/delete");
  return reply as Ack;
}

export async function programEvent(
  session: Session,
  realm: string,
  event: string,
  data: Record<string, unknown> = {},
): Promise<Ack> {
  const reply = await query(session, programCmdEvent(realm), { event, data });
  if (reply === null) throw new Error("no reply from program/cmd/event");
  return reply as Ack;
}

export async function acquireControl(
  session: Session,
  realm: string,
  clientId: string,
  user: string,
): Promise<ControlAck> {
  const reply = await query(session, controlCmdAcquire(realm), {
    client_id: clientId,
    user,
  });
  if (reply === null) throw new Error("no reply from control/cmd/acquire");
  return reply as ControlAck;
}

export async function releaseControl(
  session: Session,
  realm: string,
  clientId: string,
): Promise<ControlAck> {
  const reply = await query(session, controlCmdRelease(realm), {
    client_id: clientId,
  });
  if (reply === null) throw new Error("no reply from control/cmd/release");
  return reply as ControlAck;
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
