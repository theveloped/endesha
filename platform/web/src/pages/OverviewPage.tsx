// Cell Overview (spec §3 reduced to existing resources — no cameras, no
// events, no task feed): 3D twin left, status + engineering motion panel
// right. The twin overlays the static frame triads and the active-TCP tip
// marker (config is realm-less; fetched page-local like CamerasPage).
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { decode } from "cbor-x";
import { Button } from "@/components/ui/button";
import MotionPanel from "../components/MotionPanel";
import StatusPanel from "../components/StatusPanel";
import Viewport from "../components/Viewport";
import {
  FrameTriads,
  FlangeToolMeshes,
  FrustumOverlay,
  SceneMeshes,
  TcpDragControls,
  TcpTipMarker,
} from "../components/SceneOverlays";
import { clearProtectiveStop, sendExecutePath } from "../lib/actions";
import { queryAll, subscribeRaw } from "../lib/bus";
import {
  camImage,
  configFramesGlob,
  configIntrinsics,
  configIntrinsicsGlob,
  configSceneGlob,
  configTcpsGlob,
} from "../lib/config";
import { BASE_FRAME, frameWorldMatrix } from "../lib/framemath";
import type {
  ArmStatus,
  FlangeState,
  FrameDef,
  FrameHeader,
  Intrinsics,
  JointState,
  Pose,
  SceneObject,
  TcpDef,
} from "../lib/messages";

const TCP_FLANGE = "flange";

interface OverviewPageProps {
  session: Session | null;
  realm: string;
  jointsRef: RefObject<JointState | null>;
  jointsCountRef: RefObject<number>;
  flangeRef: RefObject<FlangeState | null>;
  status: ArmStatus | null;
  driverAlive: boolean;
  commandsEnabled: boolean;
  clientId: string;
  holdsControl: boolean;
}

export default function OverviewPage({
  session,
  realm,
  jointsRef,
  jointsCountRef,
  flangeRef,
  status,
  driverAlive,
  commandsEnabled,
  clientId,
  holdsControl,
}: OverviewPageProps) {
  const [frames, setFrames] = useState<{ name: string; def: FrameDef }[]>([]);
  const [tcps, setTcps] = useState<{ name: string; def: TcpDef }[]>([]);
  const [showFrames, setShowFrames] = useState(true);
  const [showTcp, setShowTcp] = useState(true);
  const [showScene, setShowScene] = useState(true);
  const [scene, setScene] = useState<{ name: string; obj: SceneObject }[]>([]);
  const [dragMode, setDragMode] = useState<"off" | "translate" | "rotate">(
    "off",
  );
  const [dragPending, setDragPending] = useState(false);
  const [dragError, setDragError] = useState<string | null>(null);
  const [showFrustum, setShowFrustum] = useState(true);
  const [intrinsics, setIntrinsics] = useState<Intrinsics | null>(null);
  // Latest per-frame world<-optical camera pose, fed from the image header's
  // attachment (a ref so 15 Hz frames never re-render the page).
  const cameraPoseRef = useRef<Pose | null>(null);

  useEffect(() => {
    if (session === null) return;
    void (async () => {
      try {
        const [f, t, intr, sc] = await Promise.all([
          queryAll(session, configFramesGlob()),
          queryAll(session, configTcpsGlob()),
          queryAll(session, configIntrinsicsGlob()),
          queryAll(session, configSceneGlob()),
        ]);
        setFrames(
          f.map((r) => ({
            name: r.key.replace(/^config\/frames\//, ""),
            def: r.value as FrameDef,
          })),
        );
        setTcps(
          t.map((r) => ({ name: r.key.split("/").pop()!, def: r.value as TcpDef })),
        );
        setScene(
          sc.map((r) => ({
            name: r.key.replace(/^config\/scene\//, ""),
            obj: r.value as SceneObject,
          })),
        );
        const cam = intr.find((r) => r.key === configIntrinsics());
        setIntrinsics(cam !== undefined ? (cam.value as Intrinsics) : null);
      } catch (e) {
        console.error("overview config fetch failed:", e);
      }
    })();
  }, [session]);

  // Track the camera's per-frame pose from the image topic's CBOR attachment.
  // Realm-keyed: re-subscribe on realm/session change; clears the ref so a
  // stale pose never lingers across realms.
  useEffect(() => {
    cameraPoseRef.current = null;
    if (session === null) return;
    let unsub: (() => void) | undefined;
    void (async () => {
      unsub = await subscribeRaw(session, camImage(realm), (sample) => {
        const att = sample.attachment();
        if (att === undefined) return;
        try {
          const header = decode(att.toBytes()) as FrameHeader;
          cameraPoseRef.current = header.pose ?? null;
        } catch {
          // ignore a malformed header; keep the last good pose
        }
      });
    })();
    return () => unsub?.();
  }, [session, realm]);

  const activeTcp = status?.active_tcp ?? null;
  const activeTcpDef = useMemo(
    () =>
      activeTcp === null || activeTcp === TCP_FLANGE
        ? null
        : (tcps.find((t) => t.name === activeTcp)?.def ?? null),
    [activeTcp, tcps],
  );

  // Robot base pose (Z-up world matrix); the Viewport + base-frame overlays
  // anchor to it so the canvas origin stays the WORLD frame (grid = world).
  const baseMatrix = useMemo(() => {
    const map = new Map(frames.map((fr) => [fr.name, fr.def]));
    return frameWorldMatrix(map, BASE_FRAME);
  }, [frames]);

  // Jogging is only allowed live, with the driver alive AND this browser
  // holding the control lease (the driver gates execute_path on the lease).
  // When disallowed the gizmo is forced off in render.
  const dragAllowed = commandsEnabled && driverAlive && holdsControl;

  const handleDragCommit = useCallback(
    async (
      xyz: [number, number, number],
      quat: [number, number, number, number],
    ) => {
      if (session === null || dragPending) return;
      setDragPending(true);
      setDragError(null);
      try {
        const handle = await sendExecutePath(
          session,
          realm,
          [
            {
              type: "movej",
              target: { pose: { frame: "arm/r1/base", xyz, quat } },
              speed: null,
              accel: null,
              blend_radius: 0,
            },
          ],
          { clientId },
        );
        const result = await handle.result;
        if (result.state !== "succeeded")
          setDragError(
            result.error === null
              ? result.state
              : `${result.state}: ${result.error}`,
          );
      } catch (e) {
        setDragError(e instanceof Error ? e.message : String(e));
      } finally {
        setDragPending(false);
      }
    },
    [session, realm, dragPending, clientId],
  );

  return (
    <div className="grid h-full min-h-0 grid-cols-[1fr_340px]">
      <Viewport
        jointsRef={jointsRef}
        baseMatrix={baseMatrix}
        controls={
          <>
            <Button
              variant={showFrames ? "default" : "outline"}
              size="sm"
              onClick={() => setShowFrames((v) => !v)}
            >
              Frames
            </Button>
            <Button
              variant={showTcp ? "default" : "outline"}
              size="sm"
              onClick={() => setShowTcp((v) => !v)}
            >
              TCP
            </Button>
            <Button
              variant={showFrustum ? "default" : "outline"}
              size="sm"
              onClick={() => setShowFrustum((v) => !v)}
            >
              Camera
            </Button>
            <Button
              variant={showScene ? "default" : "outline"}
              size="sm"
              onClick={() => setShowScene((v) => !v)}
            >
              Scene
            </Button>
            <Button
              variant={dragMode !== "off" ? "default" : "outline"}
              size="sm"
              disabled={!dragAllowed}
              onClick={() =>
                setDragMode((m) => (m === "off" ? "translate" : "off"))
              }
            >
              Drag TCP
            </Button>
            {dragMode !== "off" && (
              <>
                <Button
                  variant={dragMode === "translate" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setDragMode("translate")}
                >
                  Move
                </Button>
                <Button
                  variant={dragMode === "rotate" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setDragMode("rotate")}
                >
                  Rotate
                </Button>
              </>
            )}
            {dragError !== null && (
              <span className="self-center rounded bg-background/90 px-1.5 py-0.5 text-xs text-destructive">
                {dragError}
              </span>
            )}
          </>
        }
      >
        {showFrames && frames.length > 0 && <FrameTriads frames={frames} />}
        <SceneMeshes objects={scene} frames={frames} visible={showScene} />
        <FlangeToolMeshes
          objects={scene}
          flangeRef={flangeRef}
          baseMatrix={baseMatrix}
          visible={showScene}
        />
        {showFrustum && intrinsics !== null && (
          <FrustumOverlay
            intrinsics={intrinsics}
            poseRef={cameraPoseRef}
            baseMatrix={baseMatrix}
          />
        )}
        {showTcp && activeTcpDef !== null && activeTcp !== null && (
          <TcpTipMarker
            flangeRef={flangeRef}
            tcpDef={activeTcpDef}
            label={activeTcp}
            baseMatrix={baseMatrix}
          />
        )}
        {dragMode !== "off" && dragAllowed && (
          <TcpDragControls
            flangeRef={flangeRef}
            tcpDef={activeTcpDef}
            mode={dragMode === "rotate" ? "rotate" : "translate"}
            pending={dragPending}
            onCommit={handleDragCommit}
            baseMatrix={baseMatrix}
          />
        )}
      </Viewport>
      <div className="min-h-0 space-y-2 overflow-y-auto border-l border-border p-2">
        <StatusPanel
          status={status}
          driverAlive={driverAlive}
          jointsCountRef={jointsCountRef}
          flangeRef={flangeRef}
          onClearProtectiveStop={() => {
            if (session === null)
              return Promise.reject(new Error("not connected"));
            return clearProtectiveStop(session, realm);
          }}
        />
        <MotionPanel
          session={session}
          realm={realm}
          enabled={commandsEnabled && driverAlive}
          commandsEnabled={commandsEnabled}
          clientId={clientId}
          holdsControl={holdsControl}
          jointsRef={jointsRef}
          activeTcp={status?.active_tcp ?? null}
        />
      </div>
    </div>
  );
}
