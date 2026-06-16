// Operate page (gui-design-spec §4): tablet-first hold-to-jog cockpit.
//
// Hold a jog pad -> declare a cmd/jog publisher and stream JogCommand at
// 15 Hz; release -> stop the stream + undeclare (the driver's 250 ms watchdog
// halts the arm). The page sends ONLY the reference-frame name + a unit-axis
// velocity; the driver does ALL frame/TCP math. Cartesian jog is expressed in
// the selected reference frame (Base | Tool | any config frame) about the
// active TCP.
//
// Scope note: NO cmd/set_speed_scale this phase — the speed slider is a
// CLIENT-SIDE jog-speed scalar (0..1) multiplying the base jog rates before
// publishing. A bus-level set_speed_scale for programs arrives with Programs.
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import * as THREE from "three";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { sendExecutePath, stop } from "../lib/actions";
import { declarePublisher, queryAll, subscribeLatest } from "../lib/bus";
import type { BusPublisher } from "../lib/bus";
import { cmdJog, configFramesGlob, stateTcp } from "../lib/config";
import { refRotationQuat } from "../lib/framemath";
import type {
  ArmStatus,
  FrameDef,
  JogCommand,
  JointState,
  TcpState,
  Waypoint,
} from "../lib/messages";

const JOINT_BASE_RATE = 0.3; // rad/s at scale 1
const CART_LIN_RATE = 0.05; // m/s at scale 1
const CART_ANG_RATE = 0.3; // rad/s at scale 1
const JOG_HZ = 15;
const DEG_TO_RAD = Math.PI / 180;

type JogMode = "joint" | "cartesian";
type StepMode = "cont" | "10" | "1" | "0.1";

// Discrete step sizes per mode: translation in metres, rotation/joint in deg.
const STEP_LIN_M: Record<string, number> = { "10": 0.01, "1": 0.001, "0.1": 0.0001 };
const STEP_DEG: Record<string, number> = { "10": 10, "1": 1, "0.1": 0.1 };

const CART_AXES = ["X", "Y", "Z", "RX", "RY", "RZ"];
const AXIS_TINT: Record<number, string> = {
  0: "text-red-400",
  1: "text-green-400",
  2: "text-sky-400",
  3: "text-red-400",
  4: "text-green-400",
  5: "text-sky-400",
};

interface OperatePageProps {
  session: Session | null;
  realm: string;
  clientId: string;
  holdsControl: boolean;
  ownerUser: string | null;
  onAcquire: () => void;
  status: ArmStatus | null;
  jointsRef: RefObject<JointState | null>;
  driverAlive: boolean;
  commandsEnabled: boolean;
}

interface JogSession {
  token: number;
  pub: BusPublisher | null;
  timer: ReturnType<typeof setInterval> | undefined;
}

function buildVelocity(
  mode: JogMode,
  axis: number,
  sign: number,
  scale: number,
): number[] {
  const v = [0, 0, 0, 0, 0, 0];
  const rate =
    mode === "joint" ? JOINT_BASE_RATE : axis < 3 ? CART_LIN_RATE : CART_ANG_RATE;
  v[axis] = sign * rate * scale;
  return v;
}

export default function OperatePage({
  session,
  realm,
  clientId,
  holdsControl,
  ownerUser,
  onAcquire,
  status,
  jointsRef,
  driverAlive,
  commandsEnabled,
}: OperatePageProps) {
  const [frameNames, setFrameNames] = useState<string[]>([]);
  const framesRef = useRef<Map<string, FrameDef>>(new Map());
  const [selectedFrame, setSelectedFrame] = useState("base");
  const [jogScale, setJogScale] = useState(0.5);
  const [stepMode, setStepMode] = useState<StepMode>("cont");
  const [activePad, setActivePad] = useState<string | null>(null);
  const [stepPending, setStepPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [q, setQ] = useState<number[] | null>(null);
  const tcpRef = useRef<TcpState | null>(null);
  const [tcp, setTcp] = useState<TcpState | null>(null);

  const jogAllowed = commandsEnabled && driverAlive && holdsControl;
  const activeTcp = status?.active_tcp ?? "flange";

  // Static config frames for the reference-frame selector + step ref rotation.
  useEffect(() => {
    if (session === null) return;
    void (async () => {
      try {
        const rows = await queryAll(session, configFramesGlob());
        const map = new Map<string, FrameDef>();
        const names: string[] = [];
        for (const r of rows) {
          const name = r.key.replace(/^config\/frames\//, "");
          map.set(name, r.value as FrameDef);
          names.push(name);
        }
        framesRef.current = map;
        setFrameNames(names.sort());
      } catch (e) {
        console.error("operate frame fetch failed:", e);
      }
    })();
  }, [session]);

  // Live TCP (the controlled point) for the readout + cartesian step targets.
  useEffect(() => {
    if (session === null) return;
    tcpRef.current = null; // the 10 Hz tick clears the stale-realm readout
    let unsub: (() => void) | null = null;
    let disposed = false;
    void (async () => {
      const u = await subscribeLatest(
        session,
        stateTcp(realm),
        (msg) => {
          tcpRef.current = msg as TcpState;
        },
        1,
      );
      if (disposed) u();
      else unsub = u;
    })();
    return () => {
      disposed = true;
      if (unsub !== null) unsub();
    };
  }, [session, realm]);

  // 10 Hz readout copy from refs (joints + TCP mutate outside React).
  useEffect(() => {
    const timer = setInterval(() => {
      setQ(jointsRef.current ? [...jointsRef.current.q] : null);
      setTcp(tcpRef.current);
    }, 100);
    return () => clearInterval(timer);
  }, [jointsRef]);

  // ── hold-to-jog ────────────────────────────────────────────────────────
  const jogRef = useRef<JogSession | null>(null);

  const stopJog = useCallback(() => {
    const j = jogRef.current;
    jogRef.current = null;
    if (j === null) return;
    clearInterval(j.timer);
    j.pub?.undeclare();
    setActivePad(null);
  }, []);

  const startJog = useCallback(
    (mode: JogMode, axis: number, sign: number, pad: string) => {
      if (session === null || !jogAllowed) return;
      stopJog();
      setError(null);
      const token = Date.now();
      const j: JogSession = { token, pub: null, timer: undefined };
      jogRef.current = j;
      setActivePad(pad);
      const velocity = buildVelocity(mode, axis, sign, jogScale);
      const frame = mode === "joint" ? "base" : selectedFrame;
      void declarePublisher(session, cmdJog(realm)).then((pub) => {
        if (jogRef.current?.token !== token) {
          pub.undeclare(); // released before the publisher was ready
          return;
        }
        j.pub = pub;
        const send = () => {
          const cmd: JogCommand = {
            client_id: clientId,
            mode,
            frame,
            velocity,
            t: BigInt(Date.now()) * 1_000_000n,
          };
          pub.put(cmd);
        };
        send();
        j.timer = setInterval(send, 1000 / JOG_HZ);
      });
    },
    [session, realm, jogAllowed, jogScale, selectedFrame, clientId, stopJog],
  );

  // Release the jog stream if the page unmounts or control is lost mid-hold.
  useEffect(() => {
    if (!jogAllowed) stopJog();
  }, [jogAllowed, stopJog]);
  useEffect(() => () => stopJog(), [stopJog]);

  // ── discrete step nudge -> one movej goal ──────────────────────────────
  const doStep = useCallback(
    async (mode: JogMode, axis: number, sign: number) => {
      if (session === null || !jogAllowed || stepPending) return;
      if (stepMode === "cont") return;
      setStepPending(true);
      setError(null);
      try {
        let wp: Waypoint;
        if (mode === "joint") {
          const cur = jointsRef.current?.q;
          if (cur === undefined) throw new Error("no joint state");
          const target = [...cur];
          target[axis] += sign * STEP_DEG[stepMode] * DEG_TO_RAD;
          wp = {
            type: "movej",
            target: { q: target },
            speed: null,
            accel: null,
            blend_radius: 0,
          };
        } else {
          const cur = tcpRef.current;
          if (cur === null) throw new Error("no TCP pose");
          const qRef = refRotationQuat(
            framesRef.current,
            selectedFrame,
            cur.pose.quat as [number, number, number, number],
          );
          const pos = new THREE.Vector3(
            cur.pose.xyz[0],
            cur.pose.xyz[1],
            cur.pose.xyz[2],
          );
          const quat = new THREE.Quaternion(
            cur.pose.quat[0],
            cur.pose.quat[1],
            cur.pose.quat[2],
            cur.pose.quat[3],
          );
          const unit = new THREE.Vector3(
            axis % 3 === 0 ? 1 : 0,
            axis % 3 === 1 ? 1 : 0,
            axis % 3 === 2 ? 1 : 0,
          );
          if (axis < 3) {
            // translate the TCP origin along the reference-frame axis
            const disp = unit
              .clone()
              .multiplyScalar(sign * STEP_LIN_M[stepMode])
              .applyQuaternion(qRef);
            pos.add(disp);
          } else {
            // rotate about the reference-frame axis, around the TCP origin
            const axisBase = unit.clone().applyQuaternion(qRef).normalize();
            const qStep = new THREE.Quaternion().setFromAxisAngle(
              axisBase,
              sign * STEP_DEG[stepMode] * DEG_TO_RAD,
            );
            quat.premultiply(qStep);
          }
          wp = {
            type: "movej",
            target: {
              pose: {
                frame: "arm/r1/base",
                xyz: [pos.x, pos.y, pos.z],
                quat: [quat.x, quat.y, quat.z, quat.w],
              },
            },
            speed: null,
            accel: null,
            blend_radius: 0,
          };
        }
        const handle = await sendExecutePath(session, realm, [wp], { clientId });
        const result = await handle.result;
        if (result.state !== "succeeded")
          setError(
            result.error === null
              ? result.state
              : `${result.state}: ${result.error}`,
          );
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setStepPending(false);
      }
    },
    [session, realm, jogAllowed, stepPending, stepMode, selectedFrame, clientId, jointsRef],
  );

  const continuous = stepMode === "cont";

  // Pad press/release handlers: hold-to-jog in cont mode, single step otherwise.
  const padHandlers = useCallback(
    (mode: JogMode, axis: number, sign: number, pad: string) =>
      continuous
        ? {
            onPointerDown: () => startJog(mode, axis, sign, pad),
            onPointerUp: stopJog,
            onPointerLeave: stopJog,
            onPointerCancel: stopJog,
          }
        : { onClick: () => void doStep(mode, axis, sign) },
    [continuous, startJog, stopJog, doStep],
  );

  const frameOptions = useMemo(
    () => ["base", "tool", ...frameNames.filter((n) => n !== "base")],
    [frameNames],
  );

  const padBtn = (mode: JogMode, axis: number, sign: number, label: string) => {
    const pad = `${mode}:${axis}:${sign}`;
    const tint = mode === "cartesian" ? AXIS_TINT[axis] : "";
    return (
      <button
        key={pad}
        disabled={!jogAllowed || (!continuous && stepPending)}
        className={cn(
          "h-14 select-none rounded-md border border-border bg-card font-mono text-lg font-semibold tabular-nums transition-colors touch-none",
          "hover:bg-accent disabled:opacity-40",
          activePad === pad && "bg-primary text-primary-foreground",
          tint,
        )}
        {...padHandlers(mode, axis, sign, pad)}
      >
        {label}
      </button>
    );
  };

  return (
    <div className="grid h-full min-h-0 grid-cols-[320px_1fr] gap-3 p-3">
      {/* ── readout column ─────────────────────────────────────────────── */}
      <div className="min-h-0 space-y-3 overflow-y-auto">
        <div className="rounded-md border border-border p-3">
          <div className="mb-2 text-xs uppercase tracking-widest text-muted-foreground">
            Controlling TCP
          </div>
          <div className="font-mono text-sm font-semibold">{activeTcp}</div>
          {tcp !== null && (
            <div className="mt-2 grid grid-cols-3 gap-1 font-mono text-xs tabular-nums">
              {(["x", "y", "z"] as const).map((ax, i) => (
                <div key={ax}>
                  <span className="text-muted-foreground">{ax} </span>
                  {(tcp.pose.xyz[i] * 1000).toFixed(1)}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="rounded-md border border-border p-3">
          <div className="mb-2 text-xs uppercase tracking-widest text-muted-foreground">
            Joints (deg)
          </div>
          <div className="space-y-1">
            {(q ?? new Array(6).fill(0)).map((v, i) => (
              <div key={i} className="flex items-center gap-2">
                <span className="w-6 font-mono text-xs text-muted-foreground">
                  J{i + 1}
                </span>
                <div className="h-2 flex-1 overflow-hidden rounded bg-muted">
                  <div
                    className="h-full bg-primary/70"
                    style={{
                      width: `${Math.min(100, Math.abs((v / Math.PI) * 100))}%`,
                    }}
                  />
                </div>
                <span className="w-12 text-right font-mono text-xs tabular-nums">
                  {q === null ? "—" : (v / DEG_TO_RAD).toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        </div>

        <Button
          variant="destructive"
          className="h-14 w-full text-lg font-bold"
          disabled={session === null}
          onClick={() => {
            stopJog();
            if (session !== null) void stop(session, realm);
          }}
        >
          STOP
        </Button>
      </div>

      {/* ── jog column ─────────────────────────────────────────────────── */}
      <div className="relative min-h-0 overflow-y-auto rounded-md border border-border p-3">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs uppercase tracking-widest text-muted-foreground">
              Frame
            </span>
            <Select value={selectedFrame} onValueChange={setSelectedFrame}>
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {frameOptions.map((f) => (
                  <SelectItem key={f} value={f}>
                    {f === "base" ? "Base" : f === "tool" ? "Tool" : f}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-1">
            {(["cont", "10", "1", "0.1"] as StepMode[]).map((m) => (
              <Button
                key={m}
                size="sm"
                variant={stepMode === m ? "default" : "outline"}
                onClick={() => setStepMode(m)}
              >
                {m === "cont" ? "Cont" : m}
              </Button>
            ))}
            <span className="ml-1 text-xs text-muted-foreground">mm | deg</span>
          </div>
          <div className="flex flex-1 items-center gap-2">
            <span className="text-xs uppercase tracking-widest text-muted-foreground">
              Speed
            </span>
            <Slider
              className="max-w-40"
              min={0.05}
              max={1}
              step={0.05}
              value={[jogScale]}
              onValueChange={([v]) => setJogScale(v)}
            />
            <span className="w-10 font-mono text-xs tabular-nums">
              {Math.round(jogScale * 100)}%
            </span>
          </div>
        </div>

        {error !== null && (
          <div className="mb-3 rounded bg-destructive/10 px-2 py-1 text-xs text-destructive">
            {error}
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="mb-2 text-xs uppercase tracking-widest text-muted-foreground">
              Joints
            </div>
            <div className="grid grid-cols-[1fr_auto_auto] items-center gap-2">
              {[0, 1, 2, 3, 4, 5].map((j) => (
                <div key={j} className="contents">
                  <span className="font-mono text-sm text-muted-foreground">
                    J{j + 1}
                  </span>
                  {padBtn("joint", j, -1, "−")}
                  {padBtn("joint", j, 1, "+")}
                </div>
              ))}
            </div>
          </div>

          <div>
            <div className="mb-2 text-xs uppercase tracking-widest text-muted-foreground">
              Cartesian ({selectedFrame === "base" ? "Base" : selectedFrame === "tool" ? "Tool" : selectedFrame})
            </div>
            <div className="grid grid-cols-[1fr_auto_auto] items-center gap-2">
              {[0, 1, 2, 3, 4, 5].map((a) => (
                <div key={a} className="contents">
                  <span className={cn("font-mono text-sm", AXIS_TINT[a])}>
                    {CART_AXES[a]}
                  </span>
                  {padBtn("cartesian", a, -1, "−")}
                  {padBtn("cartesian", a, 1, "+")}
                </div>
              ))}
            </div>
          </div>
        </div>

        {!jogAllowed && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 rounded-md bg-background/80 backdrop-blur-sm">
            {!commandsEnabled ? (
              <span className="text-sm text-muted-foreground">
                Jogging is disabled in replay.
              </span>
            ) : !driverAlive ? (
              <span className="text-sm text-muted-foreground">
                Driver offline — jogging unavailable.
              </span>
            ) : (
              <>
                <span className="text-sm text-muted-foreground">
                  {ownerUser === null
                    ? "No one is in control."
                    : `In control: ${ownerUser}`}
                </span>
                <Button onClick={onAcquire}>Request control</Button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
