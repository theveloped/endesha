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
  cmdAcquireControl,
  cmdClearProtectiveStop,
  cmdReleaseControl,
  cmdSetDo,
  cmdSetTcp,
  cmdStop,
  configCmdDelete,
  configCmdSet,
  flowsCmdStart,
  flowsCmdStop,
  supervisorCmdSetSource,
  taskCmdAbort,
  taskCmdStart,
} from "./config";
import type {
  Ack,
  CancelReply,
  ControlAck,
  GoalFeedback,
  GoalReply,
  GoalResult,
  FlowCmdReply,
  SetSourceReply,
  TaskStartReply,
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
  const prefix = actionPrefix(realm);
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
    reply = (await query(session, `${prefix}/execute_path`, {
      goal_id: goalId,
      goal: { waypoints, client_id: clientId ?? null },
    })) as GoalReply | null;
  } catch (e) {
    undeclareBoth();
    throw e;
  }
  if (reply === null) {
    undeclareBoth();
    throw new Error("no reply from action server for execute_path");
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
  const reply = await query(session, `${actionPrefix(realm)}/cancel`, {
    goal_id: goalId,
  });
  if (reply === null) throw new Error(`no cancel reply for goal ${goalId}`);
  return reply as CancelReply;
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

export async function acquireControl(
  session: Session,
  realm: string,
  clientId: string,
  user: string,
): Promise<ControlAck> {
  const reply = await query(session, cmdAcquireControl(realm), {
    client_id: clientId,
    user,
  });
  if (reply === null) throw new Error("no reply from cmd/acquire_control");
  return reply as ControlAck;
}

export async function releaseControl(
  session: Session,
  realm: string,
  clientId: string,
): Promise<Ack> {
  const reply = await query(session, cmdReleaseControl(realm), {
    client_id: clientId,
  });
  if (reply === null) throw new Error("no reply from cmd/release_control");
  return reply as Ack;
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

export async function startTask(
  session: Session,
  realm: string,
  flow: string,
): Promise<TaskStartReply> {
  const reply = await query(session, taskCmdStart(realm, flow), {});
  if (reply === null)
    throw new Error("no reply from task/cmd/start (task_runner running?)");
  return reply as TaskStartReply;
}

export async function abortTask(
  session: Session,
  realm: string,
  flow: string,
): Promise<{ ok: boolean }> {
  const reply = await query(session, taskCmdAbort(realm, flow), {});
  if (reply === null) throw new Error("no reply from task/cmd/abort");
  return reply as { ok: boolean };
}

export async function startFlow(
  session: Session,
  realm: string,
  flow: string,
): Promise<FlowCmdReply> {
  const reply = await query(session, flowsCmdStart(realm), { flow });
  if (reply === null)
    throw new Error("no reply from flows/cmd/start (supervisor running?)");
  return reply as FlowCmdReply;
}

export async function stopFlow(
  session: Session,
  realm: string,
  flow: string,
): Promise<FlowCmdReply> {
  const reply = await query(session, flowsCmdStop(realm), { flow });
  if (reply === null)
    throw new Error("no reply from flows/cmd/stop (supervisor running?)");
  return reply as FlowCmdReply;
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
