// movej target entry (degrees or frame-referenced pose), stored poses,
// active-TCP picker, execute_path goal lifecycle with feedback progress +
// cancel, and STOP (cmd/stop). Engineering panel hosted on the Overview
// page until the Operate page exists; all command buttons carry .cmd so
// the replay realm flattens them.
import { useEffect, useRef, useState, type RefObject } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cancelGoal, configSet, sendExecutePath, setTcp, stop } from "../lib/actions";
import { queryAll } from "../lib/bus";
import {
  configFramesGlob,
  configPose,
  configPosesGlob,
  configTcpsGlob,
} from "../lib/config";
import { rpyDegToQuat } from "../lib/geometry";
import type {
  GoalResult,
  JointState,
  PoseDef,
  TcpDef,
  Waypoint,
} from "../lib/messages";

const DEG_TO_RAD = Math.PI / 180;
const RAD_TO_DEG = 180 / Math.PI;
const HOME_DEG = [0, -30, 120, -40, 90, 0];
const BASE_FRAME = "arm/r1/base";
const TCP_FLANGE = "flange";

interface ActiveGoal {
  goalId: string;
  state: string;
  progress: number;
}

interface StoredPose {
  name: string;
  q: number[];
}

type TargetMode = "joints" | "pose";

interface MotionPanelProps {
  session: Session | null;
  realm: string;
  /** Gates Move: commandsEnabled && driverAlive. */
  enabled: boolean;
  /** Gates STOP: false only in the replay realm. */
  commandsEnabled: boolean;
  /** The browser's control-lease client id, sent with execute_path goals. */
  clientId: string;
  /** True iff this browser holds the control lease — also gates Move. */
  holdsControl: boolean;
  jointsRef: RefObject<JointState | null>;
  /** Driver-reported active TCP name (status.active_tcp); null pre-status. */
  activeTcp: string | null;
}

export default function MotionPanel({
  session,
  realm,
  enabled,
  commandsEnabled,
  clientId,
  holdsControl,
  jointsRef,
  activeTcp,
}: MotionPanelProps) {
  const [degs, setDegs] = useState<string[]>(HOME_DEG.map(String));
  const [goal, setGoal] = useState<ActiveGoal | null>(null);
  const [outcome, setOutcome] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // The goal id the Cancel button targets; survives state-callback closures.
  const activeGoalIdRef = useRef<string | null>(null);

  const [mode, setMode] = useState<TargetMode>("joints");
  const [frames, setFrames] = useState<string[]>([]);
  const [frame, setFrame] = useState(BASE_FRAME);
  const [xyz, setXyz] = useState<string[]>(["0", "0", "0"]);
  const [rpy, setRpy] = useState<string[]>(["180", "0", "0"]);

  const [poses, setPoses] = useState<StoredPose[]>([]);
  const [poseName, setPoseName] = useState("");
  const [poseError, setPoseError] = useState<string | null>(null);

  const [tcps, setTcps] = useState<string[]>([]);
  const [tcpError, setTcpError] = useState<string | null>(null);

  const fetchPoses = async (s: Session) => {
    try {
      const replies = await queryAll(s, configPosesGlob());
      setPoses(
        replies
          .map((r) => ({
            name: r.key.replace(/^config\/poses\//, ""),
            q: (r.value as PoseDef).q,
          }))
          .sort((a, b) => a.name.localeCompare(b.name)),
      );
    } catch (e) {
      console.error("pose fetch failed:", e);
    }
  };

  useEffect(() => {
    if (session === null) return;
    void (async () => {
      await fetchPoses(session);
      try {
        const replies = await queryAll(session, configFramesGlob());
        const names = replies
          .map((r) => r.key.replace(/^config\/frames\//, ""))
          .filter((n) => n !== BASE_FRAME)
          .sort();
        setFrames([BASE_FRAME, ...names]);
      } catch (e) {
        console.error("frame fetch failed:", e);
        setFrames([BASE_FRAME]);
      }
      try {
        const replies = await queryAll(session, configTcpsGlob());
        const names = replies
          .filter((r) => (r.value as TcpDef).selectable_as_tcp)
          .map((r) => r.key.split("/").pop()!)
          .filter((n) => n !== TCP_FLANGE)
          .sort();
        setTcps([TCP_FLANGE, ...names]);
      } catch (e) {
        console.error("tcp fetch failed:", e);
        setTcps([TCP_FLANGE]);
      }
    })();
  }, [session]);

  const setInput = (i: number, value: string) =>
    setDegs((prev) => prev.map((v, j) => (j === i ? value : v)));
  const setXyzInput = (i: number, value: string) =>
    setXyz((prev) => prev.map((v, j) => (j === i ? value : v)));
  const setRpyInput = (i: number, value: string) =>
    setRpy((prev) => prev.map((v, j) => (j === i ? value : v)));

  const readCurrent = () => {
    const js = jointsRef.current;
    if (js === null) {
      setError("no joints sample yet");
      return;
    }
    setDegs(js.q.map((q) => (q * RAD_TO_DEG).toFixed(2)));
  };

  const applyStoredPose = (name: string) => {
    const pose = poses.find((p) => p.name === name);
    if (pose === undefined) return;
    setDegs(pose.q.map((q) => (q * RAD_TO_DEG).toFixed(2)));
  };

  const savePose = async () => {
    if (session === null) return;
    setPoseError(null);
    const js = jointsRef.current;
    if (js === null) {
      setPoseError("no joints sample yet");
      return;
    }
    const name = poseName.trim();
    if (name === "") {
      setPoseError("pose name required");
      return;
    }
    try {
      const reply = await configSet(session, configPose(name), {
        q: js.q,
        meta: {},
      });
      if (!reply.ok) {
        setPoseError(reply.error ?? "save failed");
        return;
      }
      setPoseName("");
      await fetchPoses(session);
    } catch (e) {
      setPoseError(e instanceof Error ? e.message : String(e));
    }
  };

  const pickTcp = async (name: string) => {
    if (session === null) return;
    setTcpError(null);
    try {
      const ack = await setTcp(session, realm, name);
      if (!ack.ok) setTcpError(ack.error ?? "set_tcp failed");
    } catch (e) {
      setTcpError(e instanceof Error ? e.message : String(e));
    }
  };

  const buildWaypoint = (): Waypoint | null => {
    if (mode === "joints") {
      const q = degs.map((d) => Number(d) * DEG_TO_RAD);
      if (q.some(Number.isNaN)) {
        setError("invalid joint value");
        return null;
      }
      return { type: "movej", target: { q }, speed: null, accel: null, blend_radius: 0 };
    }
    const p = xyz.map(Number);
    const r = rpy.map(Number);
    if (p.some(Number.isNaN) || r.some(Number.isNaN)) {
      setError("invalid pose value");
      return null;
    }
    return {
      type: "movej",
      target: {
        pose: { frame, xyz: p, quat: rpyDegToQuat(r[0], r[1], r[2]) },
      },
      speed: null,
      accel: null,
      blend_radius: 0,
    };
  };

  const move = async () => {
    if (session === null) return;
    setError(null);
    setOutcome(null);
    const wp = buildWaypoint();
    if (wp === null) return;
    try {
      const handle = await sendExecutePath(session, realm, [wp], {
        clientId,
        onFeedback: (fb) =>
          setGoal((g) =>
            g === null || g.goalId !== fb.goal_id
              ? g
              : { ...g, state: fb.state, progress: fb.progress },
          ),
      });
      activeGoalIdRef.current = handle.goalId;
      setGoal({ goalId: handle.goalId, state: "accepted", progress: 0 });
      const result: GoalResult = await handle.result;
      setOutcome(
        result.error === null
          ? `terminal: ${result.state}`
          : `terminal: ${result.state} — ${result.error}`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      activeGoalIdRef.current = null;
      setGoal(null);
    }
  };

  const cancel = async () => {
    const goalId = activeGoalIdRef.current;
    if (session === null || goalId === null) return;
    try {
      await cancelGoal(session, realm, goalId);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const doStop = async () => {
    if (session === null) return;
    try {
      const ack = await stop(session, realm);
      if (!ack.ok) setError(ack.error ?? "stop failed");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const moveDisabled = session === null || !enabled || !holdsControl || goal !== null;
  const cmdEnabled = session !== null && commandsEnabled;
  // No joints-ref check here: refs must not be read during render. savePose()
  // guards a missing sample with an inline error.
  const savePoseDisabled = session === null || poseName.trim() === "";

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Motion (engineering)</CardTitle>
        <CardAction>
          <Button
            variant="destructive"
            className="cmd"
            disabled={session === null || !commandsEnabled}
            onClick={() => void doStop()}
          >
            STOP
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-2">
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">TCP</span>
          <Select
            value={activeTcp ?? TCP_FLANGE}
            onValueChange={(v) => void pickTcp(v)}
            disabled={!cmdEnabled}
          >
            <SelectTrigger size="sm" className="cmd flex-1" title="active TCP">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(tcps.length > 0 ? tcps : [TCP_FLANGE]).map((name) => (
                <SelectItem key={name} value={name}>
                  {name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {tcpError !== null && (
          <p className="text-sm text-destructive">{tcpError}</p>
        )}
        <div className="flex gap-1.5">
          <Button
            variant={mode === "joints" ? "secondary" : "outline"}
            size="sm"
            onClick={() => setMode("joints")}
          >
            Joints
          </Button>
          <Button
            variant={mode === "pose" ? "secondary" : "outline"}
            size="sm"
            onClick={() => setMode("pose")}
          >
            Pose
          </Button>
        </div>
        {mode === "joints" ? (
          <>
            <div className="grid grid-cols-3 gap-1.5">
              {degs.map((value, i) => (
                <label
                  key={i}
                  className="flex items-center gap-1 text-xs text-muted-foreground"
                >
                  j{i + 1}
                  <Input
                    type="number"
                    step="0.1"
                    className="h-7 px-1.5 font-mono text-xs tabular-nums"
                    value={value}
                    onChange={(e) => setInput(i, e.target.value)}
                  />
                </label>
              ))}
            </div>
            <div className="flex items-center gap-1.5">
              <Select onValueChange={applyStoredPose}>
                <SelectTrigger size="sm" className="flex-1" title="stored pose">
                  <SelectValue placeholder="stored pose…" />
                </SelectTrigger>
                <SelectContent>
                  {poses.map((p) => (
                    <SelectItem key={p.name} value={p.name}>
                      {p.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Input
                placeholder="name"
                className="h-7 w-24 px-1.5 text-xs"
                value={poseName}
                onChange={(e) => setPoseName(e.target.value)}
              />
              <Button
                variant="outline"
                size="sm"
                className="cmd"
                disabled={savePoseDisabled}
                onClick={() => void savePose()}
              >
                Save pose
              </Button>
            </div>
            {poseError !== null && (
              <p className="text-sm text-destructive">{poseError}</p>
            )}
          </>
        ) : (
          <>
            <div className="flex items-center gap-1.5">
              <span className="text-xs text-muted-foreground">frame</span>
              <Select value={frame} onValueChange={setFrame}>
                <SelectTrigger size="sm" className="flex-1" title="target frame">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {(frames.length > 0 ? frames : [BASE_FRAME]).map((name) => (
                    <SelectItem key={name} value={name}>
                      {name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {(["x", "y", "z"] as const).map((axis, i) => (
                <label
                  key={axis}
                  className="flex items-center gap-1 text-xs text-muted-foreground"
                >
                  {axis}
                  <Input
                    type="number"
                    step="0.01"
                    className="h-7 px-1.5 font-mono text-xs tabular-nums"
                    title={`${axis} (m)`}
                    value={xyz[i]}
                    onChange={(e) => setXyzInput(i, e.target.value)}
                  />
                </label>
              ))}
            </div>
            <div className="grid grid-cols-3 gap-1.5">
              {(["r", "p", "y"] as const).map((axis, i) => (
                <label
                  key={axis}
                  className="flex items-center gap-1 text-xs text-muted-foreground"
                >
                  {axis}
                  <Input
                    type="number"
                    step="1"
                    className="h-7 px-1.5 font-mono text-xs tabular-nums"
                    title={`${axis} (deg)`}
                    value={rpy[i]}
                    onChange={(e) => setRpyInput(i, e.target.value)}
                  />
                </label>
              ))}
            </div>
          </>
        )}
        <div className="flex flex-wrap gap-1.5">
          {mode === "joints" && (
            <>
              <Button variant="outline" size="sm" onClick={readCurrent}>
                Read current
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setDegs(HOME_DEG.map(String))}
              >
                Home
              </Button>
            </>
          )}
          <Button
            size="sm"
            className="cmd"
            disabled={moveDisabled}
            onClick={() => void move()}
          >
            Move
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="cmd"
            disabled={goal === null}
            onClick={() => void cancel()}
          >
            Cancel
          </Button>
        </div>
        {goal !== null && (
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">
              goal {goal.goalId} — {goal.state}
            </p>
            <progress className="w-full" max={1} value={goal.progress} />
          </div>
        )}
        {outcome !== null && <p className="text-sm">{outcome}</p>}
        {error !== null && <p className="text-sm text-destructive">{error}</p>}
      </CardContent>
    </Card>
  );
}
