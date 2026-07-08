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
import { sendExecutePath, stop } from "../lib/actions";
import {
  declarePublisher,
  subscribeLatest,
  type BusPublisher,
} from "../lib/bus";
import { cmdJog, stateTcp } from "../lib/config";
import { refRotationQuat } from "../lib/framemath";
import type {
  FrameDef,
  JogCommand,
  JointState,
  TcpState,
  Waypoint,
} from "../lib/messages";
import { cn } from "../lib/utils";
import type { CommandCapabilities } from "./types";

const JOINT_RATE = 0.3;
const LINEAR_RATE = 0.05;
const ANGULAR_RATE = 0.3;
const JOG_HZ = 15;
const DEG_TO_RAD = Math.PI / 180;
const STEP_LINEAR_M = { "10": 0.01, "1": 0.001, "0.1": 0.0001 };
const STEP_DEG = { "10": 10, "1": 1, "0.1": 0.1 };
const CART_AXES = ["X", "Y", "Z", "RX", "RY", "RZ"];

type JogMode = "joint" | "cartesian";
type StepMode = "continuous" | "10" | "1" | "0.1";

interface JogSession {
  token: number;
  publisher: BusPublisher | null;
  timer?: ReturnType<typeof setInterval>;
}

export default function SpatialJogPalette({
  session,
  realm,
  clientId,
  capabilities,
  ownerUser,
  activeTcp,
  frames,
  jointsRef,
  onAcquire,
  onClose,
}: {
  session: Session | null;
  realm: string | null;
  clientId: string;
  capabilities: CommandCapabilities;
  ownerUser: string | null;
  activeTcp: string | null;
  frames: { name: string; def: FrameDef }[];
  jointsRef: RefObject<JointState | null>;
  onAcquire: () => void;
  onClose: () => void;
}) {
  const [referenceFrame, setReferenceFrame] = useState("base");
  const [scale, setScale] = useState(0.25);
  const [stepMode, setStepMode] = useState<StepMode>("continuous");
  const [activePad, setActivePad] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const tcpRef = useRef<TcpState | null>(null);
  const jogRef = useRef<JogSession | null>(null);

  const frameMap = useMemo(
    () => new Map(frames.map((frame) => [frame.name, frame.def])),
    [frames],
  );
  const frameNames = useMemo(
    () => ["base", "tool", ...frames.map((frame) => frame.name).filter((name) => name !== "base")],
    [frames],
  );

  useEffect(() => {
    if (session === null || realm === null) return;
    let disposed = false;
    let unsub: (() => void) | null = null;
    void (async () => {
      const release = await subscribeLatest(
        session,
        stateTcp(realm),
        (message) => {
          tcpRef.current = message as TcpState;
        },
        1,
      );
      if (disposed) release();
      else unsub = release;
    })();
    return () => {
      disposed = true;
      unsub?.();
      tcpRef.current = null;
    };
  }, [session, realm]);

  const stopJog = useCallback(() => {
    const jog = jogRef.current;
    jogRef.current = null;
    if (jog === null) return;
    if (jog.timer !== undefined) clearInterval(jog.timer);
    jog.publisher?.undeclare();
    setActivePad(null);
  }, []);

  useEffect(() => {
    if (!capabilities.jog) stopJog();
  }, [capabilities.jog, stopJog]);

  useEffect(() => {
    const stopOnBlur = () => stopJog();
    const stopWhenHidden = () => {
      if (document.hidden) stopJog();
    };
    window.addEventListener("blur", stopOnBlur);
    document.addEventListener("visibilitychange", stopWhenHidden);
    return () => {
      stopJog();
      window.removeEventListener("blur", stopOnBlur);
      document.removeEventListener("visibilitychange", stopWhenHidden);
    };
  }, [stopJog]);

  const startJog = useCallback(
    (mode: JogMode, axis: number, sign: number, pad: string) => {
      if (
        session === null ||
        realm === null ||
        !capabilities.jog ||
        stepMode !== "continuous"
      ) {
        return;
      }
      stopJog();
      setError(null);
      const rate =
        mode === "joint" ? JOINT_RATE : axis < 3 ? LINEAR_RATE : ANGULAR_RATE;
      const velocity = [0, 0, 0, 0, 0, 0];
      velocity[axis] = sign * rate * scale;
      const token = Date.now();
      const jog: JogSession = { token, publisher: null };
      jogRef.current = jog;
      setActivePad(pad);
      void declarePublisher(session, cmdJog(realm))
        .then((publisher) => {
          if (jogRef.current?.token !== token) {
            publisher.undeclare();
            return;
          }
          jog.publisher = publisher;
          const send = () => {
            const command: JogCommand = {
              client_id: clientId,
              mode,
              frame: mode === "joint" ? "base" : referenceFrame,
              velocity,
              t: BigInt(Date.now()) * 1_000_000n,
            };
            publisher.put(command);
          };
          send();
          jog.timer = setInterval(send, 1000 / JOG_HZ);
        })
        .catch((cause) => {
          stopJog();
          setError(cause instanceof Error ? cause.message : String(cause));
        });
    },
    [
      capabilities.jog,
      clientId,
      realm,
      referenceFrame,
      scale,
      session,
      stepMode,
      stopJog,
    ],
  );

  const step = useCallback(
    async (mode: JogMode, axis: number, sign: number) => {
      if (
        session === null ||
        realm === null ||
        !capabilities.motion ||
        stepMode === "continuous" ||
        pending
      ) {
        return;
      }
      setPending(true);
      setError(null);
      try {
        let waypoint: Waypoint;
        if (mode === "joint") {
          const current = jointsRef.current?.q;
          if (current === undefined) throw new Error("No joint state available.");
          const target = [...current];
          target[axis] += sign * STEP_DEG[stepMode] * DEG_TO_RAD;
          waypoint = {
            type: "movej",
            target: { q: target },
            speed: null,
            accel: null,
            blend_radius: 0,
          };
        } else {
          const current = tcpRef.current;
          if (current === null) throw new Error("No TCP state available.");
          const refQuat = refRotationQuat(
            frameMap,
            referenceFrame,
            current.pose.quat as [number, number, number, number],
          );
          const position = new THREE.Vector3(...(current.pose.xyz as [number, number, number]));
          const quaternion = new THREE.Quaternion(
            current.pose.quat[0],
            current.pose.quat[1],
            current.pose.quat[2],
            current.pose.quat[3],
          );
          const unit = new THREE.Vector3(
            axis % 3 === 0 ? 1 : 0,
            axis % 3 === 1 ? 1 : 0,
            axis % 3 === 2 ? 1 : 0,
          );
          if (axis < 3) {
            position.add(
              unit
                .multiplyScalar(sign * STEP_LINEAR_M[stepMode])
                .applyQuaternion(refQuat),
            );
          } else {
            quaternion.premultiply(
              new THREE.Quaternion().setFromAxisAngle(
                unit.applyQuaternion(refQuat).normalize(),
                sign * STEP_DEG[stepMode] * DEG_TO_RAD,
              ),
            );
          }
          waypoint = {
            type: "movej",
            target: {
              pose: {
                frame: "arm/r1/base",
                xyz: [position.x, position.y, position.z],
                quat: [quaternion.x, quaternion.y, quaternion.z, quaternion.w],
              },
            },
            speed: null,
            accel: null,
            blend_radius: 0,
          };
        }
        const handle = await sendExecutePath(session, realm, [waypoint], {
          clientId,
        });
        const result = await handle.result;
        if (!result.ok) throw new Error(result.error ?? result.state);
      } catch (cause) {
        setError(cause instanceof Error ? cause.message : String(cause));
      } finally {
        setPending(false);
      }
    },
    [
      capabilities.motion,
      clientId,
      frameMap,
      jointsRef,
      pending,
      realm,
      referenceFrame,
      session,
      stepMode,
    ],
  );

  const pad = (mode: JogMode, axis: number, sign: number, label: string) => {
    const id = `${mode}:${axis}:${sign}`;
    const handlers =
      stepMode === "continuous"
        ? {
            onPointerDown: () => startJog(mode, axis, sign, id),
            onPointerUp: stopJog,
            onPointerLeave: stopJog,
            onPointerCancel: stopJog,
          }
        : { onClick: () => void step(mode, axis, sign) };
    return (
      <button
        key={id}
        type="button"
        disabled={!capabilities.jog || pending}
        className={cn(
          "spatial-jog-button touch-none",
          activePad === id && "spatial-jog-button-active",
        )}
        {...handlers}
      >
        {label}
      </button>
    );
  };

  return (
    <section className="spatial-panel spatial-panel-strong spatial-motion-tool rounded-[28px] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="spatial-eyebrow">Active tool</p>
          <h2 className="mt-1 text-lg font-semibold">Jog arm/r1</h2>
          <p className="mt-1 text-xs text-[var(--shell-muted)]">
            TCP {activeTcp ?? "flange"} / owner {ownerUser ?? "none"}
          </p>
        </div>
        <button type="button" className="spatial-button" onClick={onClose}>
          Close
        </button>
      </div>

      {!capabilities.jog && (
        <div className="spatial-notice mt-3">
          <span>{capabilities.reason}</span>
          {capabilities.reason?.includes("Acquire") && (
            <button type="button" className="spatial-button-primary" onClick={onAcquire}>
              Acquire control
            </button>
          )}
        </div>
      )}

      <div className="mt-4 grid grid-cols-[1fr_auto] gap-3">
        <label className="spatial-field">
          <span>Reference frame</span>
          <select
            value={referenceFrame}
            onChange={(event) => setReferenceFrame(event.target.value)}
          >
            {frameNames.map((frame) => (
              <option key={frame} value={frame}>
                {frame}
              </option>
            ))}
          </select>
        </label>
        <label className="spatial-field">
          <span>Jog speed</span>
          <input
            type="range"
            min="0.05"
            max="1"
            step="0.05"
            value={scale}
            onChange={(event) => setScale(Number(event.target.value))}
          />
          <strong>{Math.round(scale * 100)}%</strong>
        </label>
      </div>

      <div className="mt-3 flex gap-2">
        {(["continuous", "10", "1", "0.1"] as StepMode[]).map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => {
              stopJog();
              setStepMode(value);
            }}
            className={cn(
              "spatial-button",
              stepMode === value && "spatial-button-selected",
            )}
          >
            {value === "continuous" ? "Continuous" : `${value} mm / deg`}
          </button>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <JogBank
          title="Joints"
          labels={["J1", "J2", "J3", "J4", "J5", "J6"]}
          renderPad={(axis, sign, label) => pad("joint", axis, sign, label)}
        />
        <JogBank
          title={`Cartesian / ${referenceFrame}`}
          labels={CART_AXES}
          renderPad={(axis, sign, label) => pad("cartesian", axis, sign, label)}
        />
      </div>

      {error !== null && <p className="spatial-error mt-3">{error}</p>}
      <button
        type="button"
        className="spatial-stop mt-4 w-full"
        disabled={session === null || realm === null}
        onClick={() => {
          stopJog();
          if (session !== null && realm !== null) void stop(session, realm);
        }}
      >
        STOP MOTION
      </button>
    </section>
  );
}

function JogBank({
  title,
  labels,
  renderPad,
}: {
  title: string;
  labels: string[];
  renderPad: (axis: number, sign: number, label: string) => React.ReactNode;
}) {
  return (
    <div>
      <p className="spatial-eyebrow mb-2">{title}</p>
      <div className="grid grid-cols-[1fr_48px_48px] items-center gap-2">
        {labels.map((label, axis) => (
          <div key={label} className="contents">
            <span className="font-mono text-xs text-[var(--shell-muted)]">{label}</span>
            {renderPad(axis, -1, "-")}
            {renderPad(axis, 1, "+")}
          </div>
        ))}
      </div>
    </div>
  );
}
