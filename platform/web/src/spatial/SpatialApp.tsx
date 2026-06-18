import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { decode } from "cbor-x";
import Viewport from "../components/Viewport";
import ReplayDrawer from "../components/ReplayDrawer";
import {
  FrameTriads,
  FrustumOverlay,
  SceneMeshes,
  TcpTipMarker,
} from "../components/SceneOverlays";
import { acquireControl, releaseControl, setTcp, stop } from "../lib/actions";
import {
  connect,
  subscribeConfigList,
  subscribeLatest,
  subscribeRaw,
  type Unsubscribe,
  watchAlive,
  watchReplaySessions,
} from "../lib/bus";
import {
  alive,
  camImage,
  CELL_NAME,
  configFramesGlob,
  configIntrinsics,
  configIntrinsicsGlob,
  configSceneGlob,
  configTcpsGlob,
  DEFAULT_WS_URL,
  realmPrefix,
  stateControlOwner,
  stateFlange,
  stateIo,
  stateJoints,
  stateStatus,
  stateTcp,
  type Realm,
} from "../lib/config";
import { BASE_FRAME, frameWorldMatrix } from "../lib/framemath";
import type {
  ArmStatus,
  ControlOwnerState,
  FlangeState,
  FrameDef,
  FrameHeader,
  Intrinsics,
  IoState,
  JointState,
  Pose,
  SceneObject,
  TcpState,
  TcpDef,
} from "../lib/messages";
import { cn } from "../lib/utils";
import { commandCapabilities } from "./capabilities";
import SpatialJogPalette from "./SpatialJogPalette";
import {
  CameraWorkspace,
  FrameWorkspace,
  IoWorkspace,
  SceneWorkspace,
  UiLab,
  WorkspaceHeader,
} from "./SpatialWorkspaces";
import type {
  ActiveTool,
  RailSection,
  RightWorkspace,
  Selection,
  UIMode,
} from "./types";
import { workspaceTitle } from "./types";

const RAIL_ITEMS: { id: RailSection; label: string; short: string }[] = [
  { id: "scene", label: "Scene", short: "SC" },
  { id: "add", label: "Add", short: "+" },
  { id: "programs", label: "Programs", short: "PR" },
  { id: "cameras", label: "Cameras", short: "CA" },
  { id: "frames", label: "Frames", short: "FR" },
  { id: "io", label: "IO", short: "IO" },
  { id: "recordings", label: "Recordings", short: "RE" },
  { id: "settings", label: "Settings", short: "ST" },
];

const MODE_META: Record<
  UIMode,
  { title: string; intent: string; accent: string }
> = {
  observe: {
    title: "Observe",
    intent: "Monitor live state without clutter or accidental actuation.",
    accent: "Inspect state",
  },
  teach: {
    title: "Teach",
    intent: "Manually position the arm, capture waypoints, and define working frames.",
    accent: "Manual setup",
  },
  build: {
    title: "Build",
    intent: "Configure the cell structure, objects, cameras, and persistent frames.",
    accent: "Cell authoring",
  },
  program: {
    title: "Program",
    intent: "Compose automation logic and bind it directly to world resources.",
    accent: "Flow logic",
  },
  debug: {
    title: "Debug / Replay",
    intent: "Review what happened over time with replay, timelines, and evidence.",
    accent: "Incident review",
  },
};

function EmptyWorldHint() {
  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <div className="spatial-panel rounded-3xl px-6 py-4 text-center">
        <p className="text-sm font-medium">Bridge disconnected</p>
        <p className="mt-1 text-xs text-[var(--shell-muted)]">
          Connect the bus to populate live cell state in the spatial shell.
        </p>
      </div>
    </div>
  );
}

export default function SpatialApp() {
  const [url] = useState(DEFAULT_WS_URL);
  const [session, setSession] = useState<Session | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [realm, setRealm] = useState<Realm>({ kind: "cell", replaySession: null });
  const [mode, setMode] = useState<UIMode>("observe");
  const [workspace, setWorkspace] = useState<RightWorkspace>({ type: "scene" });
  const [activeRail, setActiveRail] = useState<RailSection>("scene");
  const [activeTool, setActiveTool] = useState<ActiveTool>({ type: "none" });
  const [selection, setSelection] = useState<Selection | null>({
    kind: "robot",
    id: "arm/r1",
    label: "Arm r1",
  });
  const [replaySessions, setReplaySessions] = useState<string[]>([]);
  const [frames, setFrames] = useState<{ name: string; def: FrameDef }[]>([]);
  const [tcps, setTcps] = useState<{ name: string; def: TcpDef }[]>([]);
  const [scene, setScene] = useState<{ name: string; obj: SceneObject }[]>([]);
  const [intrinsics, setIntrinsics] = useState<Intrinsics | null>(null);
  const [io, setIo] = useState<IoState | null>(null);
  const [tcp, setTcpState] = useState<TcpState | null>(null);
  const [status, setStatus] = useState<ArmStatus | null>(null);
  const [controlOwner, setControlOwner] = useState<ControlOwnerState | null>(null);
  const [aliveToken, setAliveToken] = useState(false);
  const [stale, setStale] = useState(true);
  const [wsClosed, setWsClosed] = useState(false);

  const jointsRef = useRef<JointState | null>(null);
  const flangeRef = useRef<FlangeState | null>(null);
  const cameraPoseRef = useRef<Pose | null>(null);
  const lastStatusAtRef = useRef(0);

  const [clientId] = useState(() => crypto.randomUUID());
  const [user] = useState(() => localStorage.getItem("wf.user") ?? "operator");

  const prefix = realmPrefix(realm);
  const wsConnected = session !== null && !wsClosed;
  const driverAlive = wsConnected && !stale && aliveToken;
  const holdsControl =
    controlOwner?.owner != null && controlOwner.owner.client_id === clientId;
  const safetyStop = status?.estop === true || status?.protective_stop === true;
  const owner = controlOwner?.owner ?? null;
  const capabilities = useMemo(
    () =>
      commandCapabilities({
        mode,
        replay: realm.kind === "replay",
        connected: wsConnected,
        driverAlive,
        holdsControl,
        status,
      }),
    [driverAlive, holdsControl, mode, realm.kind, status, wsConnected],
  );
  const uiLab =
    new URLSearchParams(window.location.search).get("lab") === "1";

  const doConnect = useCallback(async () => {
    setConnecting(true);
    setConnectError(null);
    try {
      if (session !== null) {
        try {
          await session.close();
        } catch {
          // ignore shutdown failures while replacing the session
        }
        setSession(null);
      }
      const nextSession = await connect(url);
      lastStatusAtRef.current = Date.now();
      setWsClosed(false);
      setSession(nextSession);
    } catch (e) {
      setConnectError(e instanceof Error ? e.message : String(e));
    } finally {
      setConnecting(false);
    }
  }, [session, url]);

  useEffect(() => {
    if (session === null) return;
    const unsubs: Unsubscribe[] = [];
    let disposed = false;
    void (async () => {
      const releases = await Promise.all([
        subscribeConfigList(
          session,
          configFramesGlob(),
          "config/frames/",
          (items) =>
            setFrames(
              items.map((item) => ({
                name: item.name,
                def: item.value as FrameDef,
              })),
            ),
        ),
        subscribeConfigList(
          session,
          configTcpsGlob(),
          "config/arm/r1/tcp/",
          (items) =>
            setTcps(
              items.map((item) => ({
                name: item.name,
                def: item.value as TcpDef,
              })),
            ),
        ),
        subscribeConfigList(
          session,
          configSceneGlob(),
          "config/scene/",
          (items) =>
            setScene(
              items.map((item) => ({
                name: item.name,
                obj: item.value as SceneObject,
              })),
            ),
        ),
        subscribeConfigList(
          session,
          configIntrinsicsGlob(),
          "config/intrinsics/",
          (items) => {
            const primary = items.find(
              (item) => `config/intrinsics/${item.name}` === configIntrinsics(),
            );
            setIntrinsics((primary?.value as Intrinsics | undefined) ?? null);
          },
        ),
      ]);
      if (disposed) {
        for (const release of releases) release();
      } else {
        unsubs.push(...releases);
      }
    })();
    return () => {
      disposed = true;
      for (const release of unsubs) release();
    };
  }, [session]);

  useEffect(() => {
    if (session === null || prefix === null) return;
    const unsubs: Unsubscribe[] = [];
    let disposed = false;
    lastStatusAtRef.current = Date.now();
    jointsRef.current = null;
    flangeRef.current = null;
    cameraPoseRef.current = null;
    queueMicrotask(() => {
      if (disposed) return;
      setStatus(null);
      setControlOwner(null);
      setAliveToken(false);
      setIo(null);
      setTcpState(null);
    });
    void (async () => {
      const all = await Promise.all([
        subscribeLatest(
          session,
          stateJoints(prefix),
          (msg) => {
            jointsRef.current = msg as JointState;
          },
          1,
        ),
        subscribeLatest(
          session,
          stateFlange(prefix),
          (msg) => {
            flangeRef.current = msg as FlangeState;
          },
          1,
        ),
        subscribeLatest(
          session,
          stateStatus(prefix),
          (msg) => {
            setStatus(msg as ArmStatus);
            lastStatusAtRef.current = Date.now();
          },
          8,
        ),
        subscribeLatest(
          session,
          stateControlOwner(prefix),
          (msg) => setControlOwner(msg as ControlOwnerState),
          4,
        ),
        subscribeLatest(
          session,
          stateIo(prefix),
          (msg) => setIo(msg as IoState),
          8,
        ),
        subscribeLatest(
          session,
          stateTcp(prefix),
          (msg) => setTcpState(msg as TcpState),
          2,
        ),
        watchAlive(session, alive(prefix), setAliveToken),
        subscribeRaw(session, camImage(prefix), (sample) => {
          const attachment = sample.attachment();
          if (attachment === undefined) return;
          try {
            const header = decode(attachment.toBytes()) as FrameHeader;
            cameraPoseRef.current = header.pose ?? null;
          } catch {
            // ignore malformed attachments and keep the last valid pose
          }
        }),
      ]);
      if (disposed) {
        for (const unsub of all) unsub();
        return;
      }
      unsubs.push(...all);
    })();
    return () => {
      disposed = true;
      for (const unsub of unsubs) unsub();
    };
  }, [session, prefix]);

  useEffect(() => {
    if (session === null) return;
    let disposed = false;
    let unsub: Unsubscribe | null = null;
    void (async () => {
      const release = await watchReplaySessions(session, (sessionIds) => {
        setReplaySessions(sessionIds);
        setRealm((current) =>
          current.kind === "replay" &&
          current.replaySession !== null &&
          !sessionIds.includes(current.replaySession)
            ? { kind: "replay", replaySession: null }
            : current,
        );
      });
      if (disposed) release();
      else unsub = release;
    })();
    return () => {
      disposed = true;
      unsub?.();
    };
  }, [session]);

  useEffect(() => {
    if (session === null) return;
    const timer = setInterval(() => {
      setStale(Date.now() - lastStatusAtRef.current > 3000);
      setWsClosed(session.isClosed());
    }, 1000);
    return () => clearInterval(timer);
  }, [session]);

  const acquire = useCallback(() => {
    if (session === null || prefix === null) return;
    void acquireControl(session, prefix, clientId, user).catch((e) =>
      console.error("control acquire failed:", e),
    );
  }, [clientId, prefix, session, user]);

  const release = useCallback(() => {
    if (session === null || prefix === null) return;
    void releaseControl(session, prefix, clientId).catch((e) =>
      console.error("control release failed:", e),
    );
  }, [clientId, prefix, session]);

  useEffect(() => {
    if (!holdsControl || session === null || prefix === null) return;
    const timer = setInterval(() => acquire(), 10000);
    return () => clearInterval(timer);
  }, [holdsControl, session, prefix, acquire]);

  const activeTcpDef = useMemo(() => {
    const activeTcp = status?.active_tcp;
    if (activeTcp == null || activeTcp === "flange") return null;
    return tcps.find((tcp) => tcp.name === activeTcp)?.def ?? null;
  }, [status?.active_tcp, tcps]);

  const baseMatrix = useMemo(() => {
    const map = new Map(frames.map((frame) => [frame.name, frame.def]));
    return frameWorldMatrix(map, BASE_FRAME);
  }, [frames]);

  const treeGroups = useMemo(
    () => [
      {
        title: "Devices",
        items: [
          { kind: "robot" as const, id: "arm/r1", label: "arm/r1" },
          { kind: "camera" as const, id: "camera2d/cam0", label: "camera2d/cam0" },
        ],
      },
      {
        title: "Frames",
        items: frames.map((frame) => ({
          kind: "frame" as const,
          id: frame.name,
          label: frame.name,
        })),
      },
      {
        title: "Scene Objects",
        items: scene.map((item) => ({
          kind: "scene" as const,
          id: item.name,
          label: item.name,
        })),
      },
      {
        title: "Programs",
        items: [{ kind: "program" as const, id: "pick_test", label: "pick_test" }],
      },
    ],
    [frames, scene],
  );

  const bottomEvents = [
    owner === null ? "Control available" : `Control held by ${owner.user}`,
    status?.protective_stop ? "Protective stop active" : "Motion state nominal",
    status?.active_tcp ? `Active TCP ${status.active_tcp}` : "TCP pending",
    driverAlive ? "Driver heartbeats nominal" : "Driver stale or disconnected",
  ];

  if (uiLab) return <UiLab />;

  return (
    <div
      className={cn(
        "spatial-root spatial-grid h-full overflow-hidden",
        safetyStop && "safety-active",
      )}
      data-realm={realm.kind}
    >
      <div className="grid h-full grid-cols-[88px_1fr] grid-rows-[96px_1fr_82px]">
        <TopStatusBar
          url={url}
          onConnect={() => void doConnect()}
          connecting={connecting}
          connectError={connectError}
          realm={realm}
          onRealmChange={setRealm}
          replaySessions={replaySessions}
          mode={mode}
          onModeChange={(nextMode) => {
            setMode(nextMode);
            if (nextMode !== "teach") setActiveTool({ type: "none" });
          }}
          status={status}
          wsConnected={wsConnected}
          driverAlive={driverAlive}
          holdsControl={holdsControl}
          ownerUser={owner?.user ?? null}
          speedScale={status?.speed_scale ?? null}
          activeProgram={workspace.type === "programs" ? "Program workspace" : "Idle"}
          onAcquire={acquire}
          onRelease={release}
          onStop={() => {
            setActiveTool({ type: "none" });
            if (session !== null && prefix !== null) {
              void stop(session, prefix).catch((cause) =>
                console.error("stop failed:", cause),
              );
            }
          }}
        />
        <LeftRail
          active={activeRail}
          onSelect={(next) => {
            setActiveRail(next);
            setWorkspace(
              next === "scene"
                ? { type: "scene" }
                : next === "programs"
                  ? { type: "programs" }
                  : next === "cameras"
                    ? { type: "camera", cameraId: "cam0" }
                    : next === "frames"
                      ? {
                          type: "frame",
                          frameId:
                            selection?.kind === "frame" ? selection.id : "world",
                        }
                      : next === "io"
                        ? { type: "io" }
                        : next === "recordings"
                          ? { type: "recordings" }
                          : { type: "settings" },
            );
            if (next === "add") {
              setActiveTool({ type: "add-frame", method: "manual" });
            }
          }}
        />
        <main className="relative min-h-0 overflow-hidden">
          <Viewport
            jointsRef={jointsRef}
            baseMatrix={baseMatrix}
            robotSelected={selection?.kind === "robot"}
            onRobotSelect={() =>
              setSelection({ kind: "robot", id: "arm/r1", label: "arm/r1" })
            }
          >
            {frames.length > 0 && (
              <FrameTriads
                frames={frames}
                selectedName={
                  selection?.kind === "frame" ? selection.id : null
                }
                onSelect={(name) => {
                  setSelection({ kind: "frame", id: name, label: name });
                  setWorkspace({ type: "frame", frameId: name });
                  setActiveRail("frames");
                }}
              />
            )}
            <SceneMeshes
              objects={scene}
              frames={frames}
              visible
              selectedName={selection?.kind === "scene" ? selection.id : null}
              onSelect={(name) =>
                setSelection({ kind: "scene", id: name, label: name })
              }
            />
            {intrinsics !== null && (
              <FrustumOverlay
                intrinsics={intrinsics}
                poseRef={cameraPoseRef}
                baseMatrix={baseMatrix}
              />
            )}
            {activeTcpDef !== null && status?.active_tcp != null && (
              <TcpTipMarker
                flangeRef={flangeRef}
                tcpDef={activeTcpDef}
                label={status.active_tcp}
                baseMatrix={baseMatrix}
              />
            )}
          </Viewport>
          {!wsConnected && <EmptyWorldHint />}
          <div className="pointer-events-none absolute inset-0">
            <div className="pointer-events-auto absolute left-5 top-5 z-20 w-[340px]">
              <SceneTreeOverlay
                groups={treeGroups}
                selection={selection}
                onSelect={(next) => {
                  setSelection(next);
                  if (next.kind === "frame") {
                    setWorkspace({ type: "frame", frameId: next.id });
                    setActiveRail("frames");
                  } else if (next.kind === "camera") {
                    setWorkspace({ type: "camera", cameraId: "cam0" });
                    setActiveRail("cameras");
                  } else if (next.kind === "program") {
                    setWorkspace({ type: "programs" });
                    setActiveRail("programs");
                  }
                }}
              />
            </div>
            <div className="pointer-events-auto absolute bottom-5 left-5 z-20 w-[320px]">
              <ContextCard
                mode={mode}
                selection={selection}
                status={status}
                ownerUser={owner?.user ?? null}
                session={session}
                realm={prefix}
                tcps={tcps}
                canConfigure={capabilities.configure}
                onOpenDetails={() => {
                  if (selection?.kind === "frame") {
                    setWorkspace({ type: "frame", frameId: selection.id });
                    setActiveRail("frames");
                  } else if (selection?.kind === "camera") {
                    setWorkspace({ type: "camera", cameraId: "cam0" });
                    setActiveRail("cameras");
                  } else if (selection?.kind === "program") {
                    setWorkspace({ type: "programs" });
                    setActiveRail("programs");
                  } else {
                    setWorkspace({ type: "scene" });
                    setActiveRail("scene");
                  }
                }}
                onPrimaryAction={() => {
                  if (selection?.kind === "robot" && mode === "teach") {
                    setActiveTool({ type: "jog", armId: selection.id });
                    return;
                  }
                  if (selection?.kind === "frame") {
                    setWorkspace({ type: "frame", frameId: selection.id });
                  }
                }}
              />
            </div>
            {activeTool.type !== "none" && (
              <div className="pointer-events-auto absolute bottom-5 left-1/2 z-30 w-[min(760px,calc(100%-40px))] -translate-x-1/2">
                {activeTool.type === "jog" ? (
                  <SpatialJogPalette
                    session={session}
                    realm={prefix}
                    clientId={clientId}
                    capabilities={capabilities}
                    ownerUser={owner?.user ?? null}
                    activeTcp={status?.active_tcp ?? null}
                    frames={frames}
                    jointsRef={jointsRef}
                    onAcquire={acquire}
                    onClose={() => setActiveTool({ type: "none" })}
                  />
                ) : (
                  <FrameWorkspace
                    session={session}
                    frameId={
                      selection?.kind === "frame" ? selection.id : "new frame"
                    }
                    frame={
                      selection?.kind === "frame"
                        ? (frames.find((item) => item.name === selection.id)?.def ??
                          null)
                        : null
                    }
                    tcp={tcp}
                    capabilities={capabilities}
                  />
                )}
              </div>
            )}
            <div className="pointer-events-auto absolute right-5 top-5 z-20 h-[calc(100%-40px)] w-[min(46vw,680px)]">
              <SpatialWorkspace
                session={session}
                realm={prefix}
                realmState={realm}
                workspace={workspace}
                mode={mode}
                selection={selection}
                status={status}
                frames={frames}
                io={io}
                tcp={tcp}
                connected={wsConnected}
                capabilities={capabilities}
                replaySessions={replaySessions}
                onPickReplay={(sid) =>
                  setRealm({ kind: "replay", replaySession: sid })
                }
                onClose={() => setWorkspace({ type: "closed" })}
              />
            </div>
          </div>
        </main>
        <BottomTimeline
          mode={mode}
          realm={realm}
          events={bottomEvents}
          driverAlive={driverAlive}
        />
      </div>
    </div>
  );
}

function TopStatusBar(props: {
  url: string;
  onConnect: () => void;
  connecting: boolean;
  connectError: string | null;
  realm: Realm;
  onRealmChange: (realm: Realm) => void;
  replaySessions: string[];
  mode: UIMode;
  onModeChange: (mode: UIMode) => void;
  status: ArmStatus | null;
  wsConnected: boolean;
  driverAlive: boolean;
  holdsControl: boolean;
  ownerUser: string | null;
  speedScale: number | null;
  activeProgram: string;
  onAcquire: () => void;
  onRelease: () => void;
  onStop: () => void;
}) {
  const {
    url,
    onConnect,
    connecting,
    connectError,
    realm,
    onRealmChange,
    replaySessions,
    mode,
    onModeChange,
    status,
    wsConnected,
    driverAlive,
    holdsControl,
    ownerUser,
    speedScale,
    activeProgram,
    onAcquire,
    onRelease,
    onStop,
  } = props;

  return (
    <header className="spatial-panel spatial-panel-strong col-span-2 mx-4 mt-4 grid grid-cols-[220px_1fr_auto] items-center gap-4 rounded-[28px] px-5 py-3">
      <div className="flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--shell-line)] bg-black/20 font-mono text-sm font-semibold text-[var(--shell-accent-strong)]">
          WF
        </div>
        <div>
          <div className="flex items-center gap-2">
            <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
              Cell
            </p>
            <span
              className={cn(
                "inline-block h-2.5 w-2.5 rounded-full",
                wsConnected ? "bg-emerald-300" : "bg-rose-300",
              )}
            />
          </div>
          <p className="text-lg font-semibold">{CELL_NAME}</p>
          <p className="text-xs text-[var(--shell-muted)]">
            3D-first commissioning / {activeProgram}
          </p>
        </div>
      </div>
      <div className="flex items-center justify-center gap-3">
        <SelectChipGroup
          value={realm.kind}
          options={[
            { value: "cell", label: "Live" },
            { value: "replay", label: "Replay" },
          ]}
          onChange={(value) => {
            if (value === "replay") {
              onRealmChange({
                kind: "replay",
                replaySession: replaySessions.length === 1 ? replaySessions[0] : null,
              });
              return;
            }
            onRealmChange({ kind: "cell", replaySession: null });
          }}
        />
        <SelectChipGroup
          value={mode}
          options={(
            ["observe", "teach", "build", "program", "debug"] as UIMode[]
          ).map((item) => ({
            value: item,
            label: MODE_META[item].title,
          }))}
          onChange={(value) => onModeChange(value as UIMode)}
        />
      </div>
      <div className="flex items-center justify-end gap-3">
        <button
          type="button"
          onClick={onConnect}
          title={`Bridge ${url}`}
          className="spatial-button"
        >
          {connecting ? "Connecting" : wsConnected ? "Reconnect" : "Connect"}
        </button>
        <StatusChip
          label="Safety"
          value={
            status?.estop ? "E-Stop" : status?.protective_stop ? "P-Stop" : "OK"
          }
          tone={status?.estop || status?.protective_stop ? "danger" : "ok"}
        />
        <StatusChip
          label="Speed"
          value={speedScale == null ? "-" : `${Math.round(speedScale * 100)}%`}
          tone="muted"
        />
        <button
          type="button"
          onClick={holdsControl ? onRelease : onAcquire}
          disabled={!driverAlive && !holdsControl}
          className={cn(
            "rounded-2xl border px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] transition disabled:opacity-50",
            holdsControl
              ? "border-emerald-400/30 bg-emerald-400/12 text-emerald-200"
              : "border-[var(--shell-line)] bg-white/5 text-[var(--shell-text)]",
          )}
        >
          {holdsControl ? `Release / ${ownerUser ?? "you"}` : `Acquire / ${ownerUser ?? "none"}`}
        </button>
        <button
          type="button"
          onClick={onStop}
          disabled={!driverAlive || realm.kind === "replay"}
          className="rounded-2xl border border-rose-400/30 bg-rose-500/16 px-4 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-100"
        >
          Stop
        </button>
      </div>
      {connectError !== null && (
        <div className="col-span-3 mt-2 text-right text-xs text-rose-300">
          {connectError}
        </div>
      )}
    </header>
  );
}

function LeftRail(props: {
  active: RailSection;
  onSelect: (section: RailSection) => void;
}) {
  return (
    <aside className="mx-3 mb-4 mt-5 flex min-h-0 flex-col gap-2">
      {RAIL_ITEMS.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => props.onSelect(item.id)}
          className={cn(
            "spatial-panel flex h-14 flex-col items-center justify-center rounded-3xl text-center transition",
            props.active === item.id && "spatial-selection-ring bg-white/8",
          )}
          title={item.label}
        >
          <span className="font-mono text-xs text-[var(--shell-accent-strong)]">
            {item.short}
          </span>
          <span className="mt-1 text-[10px] uppercase tracking-[0.22em] text-[var(--shell-muted)]">
            {item.label}
          </span>
        </button>
      ))}
    </aside>
  );
}

function SceneTreeOverlay(props: {
  groups: { title: string; items: Selection[] }[];
  selection: Selection | null;
  onSelect: (selection: Selection) => void;
}) {
  return (
    <section className="spatial-panel spatial-scrollbar max-h-[38vh] overflow-auto rounded-[28px] px-4 py-4">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.26em] text-[var(--shell-muted)]">
            Scene
          </p>
          <p className="text-sm font-semibold">Spatial navigation tree</p>
        </div>
        <span className="rounded-full border border-[var(--shell-line)] px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-[var(--shell-muted)]">
          Context first
        </span>
      </div>
      <input
        value=""
        readOnly
        className="mb-4 w-full rounded-2xl border border-[var(--shell-line)] bg-black/15 px-3 py-2 text-xs text-[var(--shell-muted)] outline-none"
        placeholder="Search will land in the next milestone"
      />
      <div className="space-y-4">
        {props.groups.map((group) => (
          <div key={group.title}>
            <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--shell-muted)]">
              {group.title}
            </p>
            <div className="space-y-1">
              {group.items.map((item) => {
                const selected =
                  props.selection?.kind === item.kind &&
                  props.selection.id === item.id;
                return (
                  <button
                    key={`${item.kind}:${item.id}`}
                    type="button"
                    onClick={() => props.onSelect(item)}
                    className={cn(
                      "flex w-full items-center justify-between rounded-2xl px-3 py-2 text-left transition",
                      selected
                        ? "bg-[var(--shell-glow)] text-white"
                        : "bg-white/[0.03] text-[var(--shell-text)] hover:bg-white/[0.06]",
                    )}
                  >
                    <span className="text-sm">{item.label}</span>
                    <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-[var(--shell-muted)]">
                      {item.kind}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function ContextCard(props: {
  mode: UIMode;
  selection: Selection | null;
  status: ArmStatus | null;
  ownerUser: string | null;
  session: Session | null;
  realm: string | null;
  tcps: { name: string; def: TcpDef }[];
  canConfigure: boolean;
  onPrimaryAction: () => void;
  onOpenDetails: () => void;
}) {
  const [tcpError, setTcpError] = useState<string | null>(null);
  if (props.selection === null) return null;
  const modeMeta = MODE_META[props.mode];
  const body =
    props.selection.kind === "robot"
      ? {
          title: "Arm r1",
          summary: `Mode ${props.status?.mode ?? "unknown"} / TCP ${props.status?.active_tcp ?? "-"}`,
          intent:
            props.mode === "teach"
              ? "Manual motion and teaching should stay lightweight and spatial."
              : "Inspect robot status before opening a deeper workspace.",
          primary: props.mode === "teach" ? "Jog" : "Open scene view",
        }
      : props.selection.kind === "camera"
        ? {
            title: "Camera cam0",
            summary: "Eye-in-hand vision source / preview and calibration entry",
            intent: "Small preview actions belong here; calibration expands on the right.",
            primary: "Open camera",
          }
        : props.selection.kind === "frame"
          ? {
              title: `Frame ${props.selection.label}`,
              summary: "Contextual frame detail with parent, source, and consumers",
              intent: "This card clarifies why the frame exists before numerical editing.",
              primary: "Open frame",
            }
          : props.selection.kind === "scene"
            ? {
                title: props.selection.label,
                summary: "Scene object anchored to the cell graph",
                intent: "Build-mode transforms should stay near the selected object.",
                primary: "Inspect object",
              }
            : {
                title: props.selection.label,
                summary: "Program workspace keeps graph logic linked to the world.",
                intent: "Program editing should highlight resources in the 3D scene.",
                primary: "Open program",
              };

  return (
    <section className="spatial-panel rounded-[28px] px-4 py-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
            {props.selection.kind}
          </p>
          <h2 className="mt-1 text-lg font-semibold">{body.title}</h2>
        </div>
        <span className="rounded-full border border-[var(--shell-line)] px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-[var(--shell-accent-strong)]">
          {modeMeta.accent}
        </span>
      </div>
      <p className="text-sm text-[var(--shell-text)]">{body.summary}</p>
      <p className="mt-2 text-xs leading-5 text-[var(--shell-muted)]">{body.intent}</p>
      {props.selection.kind === "robot" && (
        <>
          <p className="mt-3 text-xs text-[var(--shell-muted)]">
            Control owner: {props.ownerUser ?? "none"}
          </p>
          <label className="spatial-field mt-3">
            <span>Active TCP</span>
            <select
              value={props.status?.active_tcp ?? "flange"}
              disabled={
                props.session === null ||
                props.realm === null ||
                !props.canConfigure
              }
              onChange={(event) => {
                if (props.session === null || props.realm === null) return;
                setTcpError(null);
                void setTcp(props.session, props.realm, event.target.value)
                  .then((reply) => {
                    if (!reply.ok) {
                      setTcpError(reply.error ?? "TCP selection failed.");
                    }
                  })
                  .catch((cause) =>
                    setTcpError(
                      cause instanceof Error ? cause.message : String(cause),
                    ),
                  );
              }}
            >
              <option value="flange">flange</option>
              {props.tcps.map((tcpDefinition) => (
                <option key={tcpDefinition.name} value={tcpDefinition.name}>
                  {tcpDefinition.name}
                </option>
              ))}
            </select>
          </label>
          {tcpError !== null && <p className="spatial-error mt-2">{tcpError}</p>}
        </>
      )}
      <div className="mt-4 flex gap-2">
        <button
          type="button"
          onClick={props.onPrimaryAction}
          className="rounded-2xl bg-[var(--shell-accent)] px-3 py-2 text-xs font-semibold text-slate-950"
        >
          {body.primary}
        </button>
        <button
          type="button"
          onClick={props.onOpenDetails}
          className="rounded-2xl border border-[var(--shell-line)] px-3 py-2 text-xs font-medium"
        >
          Open details
        </button>
      </div>
    </section>
  );
}

function SpatialWorkspace(props: {
  session: Session | null;
  realm: string | null;
  realmState: Realm;
  workspace: RightWorkspace;
  mode: UIMode;
  selection: Selection | null;
  status: ArmStatus | null;
  frames: { name: string; def: FrameDef }[];
  io: IoState | null;
  tcp: TcpState | null;
  connected: boolean;
  capabilities: ReturnType<typeof commandCapabilities>;
  replaySessions: string[];
  onPickReplay: (sid: string) => void;
  onClose: () => void;
}) {
  if (props.workspace.type === "closed") return null;
  const frameId =
    props.workspace.type === "frame" ? props.workspace.frameId : null;
  const description =
    props.workspace.type === "camera"
      ? "Preview and tune the selected camera while the cell remains visible."
      : props.workspace.type === "frame"
        ? "Inspect frame semantics and capture a new frame from the current TCP."
        : props.workspace.type === "io"
          ? "Inspect every channel; writes remain lease- and realm-gated."
          : props.workspace.type === "recordings"
            ? "Replay transport stays connected to the same world and selection model."
            : MODE_META[props.mode].intent;
  return (
    <section className="spatial-panel spatial-panel-strong spatial-scrollbar h-full overflow-auto rounded-[32px] p-5">
      <WorkspaceHeader
        eyebrow="Right workspace"
        title={workspaceTitle(props.workspace)}
        description={description}
        onClose={props.onClose}
      />
      {props.workspace.type === "scene" && (
        <SceneWorkspace
          mode={props.mode}
          selection={props.selection}
          status={props.status}
        />
      )}
      {props.workspace.type === "camera" && (
        <CameraWorkspace
          session={props.session}
          realm={props.realm}
          connected={props.connected}
          capabilities={props.capabilities}
        />
      )}
      {props.workspace.type === "io" && (
        <IoWorkspace
          session={props.session}
          realm={props.realm}
          io={props.io}
          connected={props.connected}
          capabilities={props.capabilities}
        />
      )}
      {props.workspace.type === "frame" && (
        <FrameWorkspace
          session={props.session}
          frameId={frameId ?? "world"}
          frame={
            props.frames.find((frame) => frame.name === frameId)?.def ?? null
          }
          tcp={props.tcp}
          capabilities={props.capabilities}
        />
      )}
      {props.workspace.type === "recordings" && (
        <ReplayDrawer
          session={props.session}
          sid={props.realmState.replaySession}
          sessions={props.replaySessions}
          onPickSession={props.onPickReplay}
        />
      )}
      {props.workspace.type === "programs" && (
        <p className="spatial-notice">
          Program authoring is intentionally deferred from the commissioning
          release. Existing programs remain available in the legacy UI.
        </p>
      )}
      {props.workspace.type === "settings" && (
        <div className="space-y-3">
          <p className="spatial-notice">
            Open <code>?lab=1</code> to review the complete spatial UI kit.
          </p>
          <a className="spatial-button inline-flex" href="/">
            Open legacy UI
          </a>
        </div>
      )}
    </section>
  );
}

function BottomTimeline(props: {
  mode: UIMode;
  realm: Realm;
  events: string[];
  driverAlive: boolean;
}) {
  return (
    <footer className="col-span-2 mx-4 mb-4 mt-2 flex items-center gap-4 overflow-hidden rounded-[24px] border border-[var(--shell-line)] bg-black/18 px-5 py-3">
      <div className="min-w-40">
        <p className="spatial-eyebrow">Timeline / events</p>
        <p className="mt-1 text-xs text-[var(--shell-muted)]">
          {props.mode === "debug" ? "Replay scrubber" : "Recent cell evidence"}
        </p>
      </div>
      <div className="flex min-w-0 flex-1 gap-2 overflow-hidden">
        {props.events.map((event) => (
          <div
            key={event}
            className="min-w-0 flex-1 truncate rounded-xl border border-[var(--shell-line)] bg-white/[0.03] px-3 py-2 text-xs text-[var(--shell-text)]"
            title={event}
          >
            {event}
          </div>
        ))}
      </div>
      <span className="spatial-chip spatial-chip-muted">
        {props.realm.kind}
      </span>
      <span
        className={cn(
          "spatial-chip",
          props.driverAlive ? "spatial-chip-ok" : "spatial-chip-warn",
        )}
      >
        {props.driverAlive ? "Heartbeat" : "Stale"}
      </span>
    </footer>
  );
}

function SelectChipGroup(props: {
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}) {
  return (
    <div className="rounded-2xl border border-[var(--shell-line)] bg-black/15 p-1">
      <div className="flex gap-1">
        {props.options.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => props.onChange(option.value)}
            className={cn(
              "rounded-xl px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] transition",
              props.value === option.value
                ? "bg-[var(--shell-accent)] text-slate-950"
                : "text-[var(--shell-muted)] hover:text-[var(--shell-text)]",
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function StatusChip(props: {
  label: string;
  value: string;
  tone: "ok" | "danger" | "muted";
}) {
  return (
    <div className="spatial-pill rounded-2xl px-3 py-2">
      <p className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--shell-muted)]">
        {props.label}
      </p>
      <p
        className={cn(
          "mt-1 text-xs font-semibold",
          props.tone === "ok" && "text-emerald-200",
          props.tone === "danger" && "text-rose-200",
          props.tone === "muted" && "text-[var(--shell-text)]",
        )}
      >
        {props.value}
      </p>
    </div>
  );
}
