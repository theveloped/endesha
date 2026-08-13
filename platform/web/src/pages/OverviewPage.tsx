// Cell Overview (spec §3 reduced to existing resources — no cameras, no
// events, no task feed): 3D twin left, status + engineering motion panel
// right. The twin overlays the static frame triads and the active-TCP tip
// marker (config is realm-less; fetched page-local like CamerasPage).
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { decode } from "cbor-x";
import DeviceTree from "../components/DeviceTree";
import MotionPanel from "../components/MotionPanel";
import StatusPanel from "../components/StatusPanel";
import Viewport from "../components/Viewport";
import { ViewportLegend } from "../components/ViewportLegend";
import {
  FrameTriads,
  FlangeToolMeshes,
  FrustumOverlay,
  PoseGhost,
  SceneMeshes,
  TcpDragControls,
  TcpTipMarker,
} from "../components/SceneOverlays";
import { clearProtectiveStop } from "../lib/actions";
import { queryAll, subscribeRaw } from "../lib/bus";
import {
  camImage,
  CID,
  configFramesGlob,
  configIntrinsics,
  configIntrinsicsGlob,
  configSceneGlob,
  configTcpsGlob,
  RID,
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
import type { ScenePreview } from "../scene/types";
import type {
  TcpDragMode,
  ViewerVisibility,
} from "../scene/viewerControls";
import {
  isSceneItemHidden,
  sceneGroupVisibilityId,
  sceneItemVisibilityId,
} from "../scene/visibility";

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
  workspace?: boolean;
  preview?: ScenePreview;
  configurationRevision?: number;
  visibility: ViewerVisibility;
  onVisibilityChange: (visibility: ViewerVisibility) => void;
  hiddenSceneItems: ReadonlySet<string>;
  dragMode: TcpDragMode;
  dragPending: boolean;
  onDragCommit: (
    xyz: [number, number, number],
    quat: [number, number, number, number],
  ) => void;
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
  workspace = false,
  preview = null,
  configurationRevision = 0,
  visibility,
  onVisibilityChange,
  hiddenSceneItems,
  dragMode,
  dragPending,
  onDragCommit,
}: OverviewPageProps) {
  const [frames, setFrames] = useState<{ name: string; def: FrameDef }[]>([]);
  const [tcps, setTcps] = useState<{ name: string; def: TcpDef }[]>([]);
  const [scene, setScene] = useState<{ name: string; obj: SceneObject }[]>([]);
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
  }, [session, configurationRevision]);

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
  const filteredScene = useMemo(() => {
    const worldHidden = hiddenSceneItems.has("world");
    const deviceGroupHidden = hiddenSceneItems.has(
      sceneGroupVisibilityId("devices"),
    );
    const frameByName = new Map(frames.map((frame) => [frame.name, frame.def]));
    const frameHiddenCache = new Map<string, boolean>();
    const frameTreeHidden = (name: string, visiting = new Set<string>()): boolean => {
      const cached = frameHiddenCache.get(name);
      if (cached !== undefined) return cached;
      if (worldHidden) return true;
      const arm = /^arm\/([^/]+)\//.exec(name)?.[1];
      if (
        arm !== undefined &&
        (deviceGroupHidden ||
          hiddenSceneItems.has(sceneItemVisibilityId("device", arm)))
      ) {
        frameHiddenCache.set(name, true);
        return true;
      }
      if (hiddenSceneItems.has(sceneItemVisibilityId("frame", name))) {
        frameHiddenCache.set(name, true);
        return true;
      }
      if (visiting.has(name)) return false;
      const parent = frameByName.get(name)?.parent;
      if (parent === undefined || parent === "world") {
        frameHiddenCache.set(name, false);
        return false;
      }
      const nextVisiting = new Set(visiting);
      nextVisiting.add(name);
      const hidden = frameTreeHidden(parent, nextVisiting);
      frameHiddenCache.set(name, hidden);
      return hidden;
    };
    const framesVisible =
      !hiddenSceneItems.has(sceneGroupVisibilityId("frames"));
    const objectsVisible =
      !hiddenSceneItems.has(sceneGroupVisibilityId("objects"));
    return {
      worldHidden,
      robotVisible:
        !worldHidden &&
        !deviceGroupHidden &&
        !hiddenSceneItems.has(sceneItemVisibilityId("device", RID)),
      cameraVisible:
        !worldHidden &&
        !deviceGroupHidden &&
        !hiddenSceneItems.has(sceneItemVisibilityId("device", CID)),
      frames: framesVisible
        ? frames.filter((frame) => !frameTreeHidden(frame.name))
        : [],
      objects: objectsVisible
        ? scene.filter(
            (object) =>
              !hiddenSceneItems.has(
                sceneItemVisibilityId("object", object.name),
              ) && !frameTreeHidden(object.obj.frame),
          )
        : [],
    };
  }, [frames, hiddenSceneItems, scene]);

  const tcpVisible =
    filteredScene.robotVisible &&
    !isSceneItemHidden(hiddenSceneItems, "tcp", activeTcp ?? "");
  const previewVisible =
    preview === null ||
    (preview.kind === "pose"
      ? filteredScene.robotVisible &&
        !isSceneItemHidden(hiddenSceneItems, "pose", preview.name)
      : filteredScene.robotVisible &&
        !isSceneItemHidden(hiddenSceneItems, "tcp", preview.name));

  // Jogging is only allowed live, with the driver alive AND this browser
  // holding the control lease (the driver gates execute_path on the lease).
  // When disallowed the gizmo is forced off in render.
  const dragAllowed = commandsEnabled && driverAlive && holdsControl;


  return (
    <div
      className={
        workspace
          ? "h-full min-h-0"
          : "grid h-full min-h-0 grid-cols-[1fr_340px]"
      }
    >
      <Viewport
        jointsRef={jointsRef}
        baseMatrix={baseMatrix}
        robotVisible={filteredScene.robotVisible}
        topRight={
          workspace ? undefined : (
            <DeviceTree
              session={session}
              realm={realm}
              commandsEnabled={commandsEnabled}
            />
          )
        }
        legend={
          <ViewportLegend
            visibility={visibility}
            onChange={onVisibilityChange}
          />
        }
      >
        {visibility.frames && filteredScene.frames.length > 0 && (
          <FrameTriads frames={filteredScene.frames} />
        )}
        <SceneMeshes
          objects={filteredScene.objects}
          frames={frames}
          visible={visibility.scene}
        />
        <FlangeToolMeshes
          objects={filteredScene.objects}
          flangeRef={flangeRef}
          baseMatrix={baseMatrix}
          visible={visibility.scene}
        />
        {visibility.camera && filteredScene.cameraVisible && intrinsics !== null && (
          <FrustumOverlay
            intrinsics={intrinsics}
            poseRef={cameraPoseRef}
            baseMatrix={baseMatrix}
          />
        )}
        {visibility.tcp && tcpVisible && activeTcpDef !== null && activeTcp !== null && (
          <TcpTipMarker
            flangeRef={flangeRef}
            tcpDef={activeTcpDef}
            label={activeTcp}
            baseMatrix={baseMatrix}
          />
        )}
        {previewVisible && preview?.kind === "pose" && (
          <PoseGhost q={preview.q} baseMatrix={baseMatrix} />
        )}
        {previewVisible && preview?.kind === "tcp" && (
          <TcpTipMarker
            flangeRef={flangeRef}
            tcpDef={preview.def}
            label={preview.name}
            baseMatrix={baseMatrix}
          />
        )}
        {dragMode !== "off" && dragAllowed && (
          <TcpDragControls
            flangeRef={flangeRef}
            tcpDef={activeTcpDef}
            mode={dragMode === "rotate" ? "rotate" : "translate"}
            pending={dragPending}
            onCommit={onDragCommit}
            baseMatrix={baseMatrix}
          />
        )}
      </Viewport>
      {!workspace && (
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
      )}
    </div>
  );
}
