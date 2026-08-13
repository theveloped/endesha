import {
  useCallback,
  useEffect,
  useState,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import {
  ChevronRight,
  CircleGauge,
  Cpu,
  Database,
  GitBranch,
  Moon,
  Network,
  Square,
  Sun,
  X,
} from "lucide-react";
import { Badge } from "../catalyst/badge";
import { Button } from "../catalyst/button";
import { Input } from "../catalyst/input";
import { Navbar, NavbarLabel } from "../catalyst/navbar";
import {
  Sidebar,
  SidebarBody,
  SidebarFooter,
  SidebarHeader,
  SidebarHeading,
  SidebarItem,
  SidebarLabel,
  SidebarSection,
  SidebarSpacer,
} from "../catalyst/sidebar";
import { SidebarLayout } from "../catalyst/sidebar-layout";
import DeviceTree from "../components/DeviceTree";
import MotionPanel from "../components/MotionPanel";
import ReplayDrawer from "../components/ReplayDrawer";
import { TcpDragPanel } from "../components/TcpDragPanel";
import StatusPanel from "../components/StatusPanel";
import CamerasPage from "../pages/CamerasPage";
import FramesPage from "../pages/FramesPage";
import IoPage from "../pages/IoPage";
import OperatePage from "../pages/OperatePage";
import OverviewPage from "../pages/OverviewPage";
import TopicsPage from "../pages/TopicsPage";
import { clearProtectiveStop, sendExecutePath, stop } from "../lib/actions";
import { CELL_NAME } from "../lib/config";
import { useRuntime } from "../runtime/context";
import { SceneCreatePanel } from "../scene/SceneCreatePanel";
import { SceneDetails } from "../scene/SceneDetails";
import { SceneGroupTable } from "../scene/SceneGroupTable";
import { SceneHierarchy } from "../scene/SceneHierarchy";
import type {
  SceneCreateKind,
  SceneCreateRequest,
  SceneGroupKind,
  ScenePreview,
  SceneSelection,
} from "../scene/types";
import {
  useSceneStructure,
  type SceneStructure,
} from "../scene/useSceneStructure";
import {
  DEFAULT_VIEWER_VISIBILITY,
  type TcpDragMode,
  type ViewerVisibility,
} from "../scene/viewerControls";
import {
  TOOL_META,
  ToolRibbon,
  type WorkspaceTool,
} from "./ToolRibbon";

type Theme = "light" | "dark";

const LEFT_DEFAULT = 300;
const RIGHT_DEFAULT: Record<WorkspaceTool, number> = {
  overview: 360,
  operate: 560,
  io: 540,
  cameras: 620,
  configuration: 620,
  topics: 720,
};

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function useRememberedWidth(
  key: string,
  initial: number,
  min: number,
  max: number,
) {
  const [widths, setWidths] = useState<Record<string, number>>({});
  const stored = Number(localStorage.getItem(key));
  const current =
    widths[key] ??
    (Number.isFinite(stored) && stored > 0 ? stored : initial);
  const width = clamp(current, min, max);
  const update = useCallback(
    (next: number) => {
      const value = clamp(next, min, max);
      setWidths((previous) => ({ ...previous, [key]: value }));
      localStorage.setItem(key, String(value));
    },
    [key, min, max],
  );
  return [width, update] as const;
}

function ResizeHandle({
  edge,
  width,
  onWidth,
  onReset,
}: {
  edge: "left" | "right";
  width: number;
  onWidth: (width: number) => void;
  onReset: () => void;
}) {
  const start = (event: ReactPointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    const originX = event.clientX;
    const originWidth = width;
    const target = event.currentTarget;
    const move = (next: PointerEvent) => {
      const delta = next.clientX - originX;
      onWidth(originWidth + (edge === "right" ? delta : -delta));
    };
    const end = () => {
      target.removeEventListener("pointermove", move);
      target.removeEventListener("pointerup", end);
      target.removeEventListener("pointercancel", end);
    };
    target.addEventListener("pointermove", move);
    target.addEventListener("pointerup", end);
    target.addEventListener("pointercancel", end);
  };

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize panel"
      title="Drag to resize; double-click to reset"
      onPointerDown={start}
      onDoubleClick={onReset}
      className={`absolute inset-y-0 z-20 w-2 cursor-col-resize touch-none outline-none after:absolute after:inset-y-0 after:left-1/2 after:w-px after:-translate-x-1/2 after:bg-transparent hover:after:bg-blue-500 ${
        edge === "right" ? "-right-1" : "-left-1"
      }`}
    />
  );
}

function ResizablePane({
  side,
  width,
  onWidth,
  onReset,
  className = "",
  children,
}: {
  side: "left" | "right";
  width: number;
  onWidth: (width: number) => void;
  onReset: () => void;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={`@container relative h-full shrink-0 bg-white dark:bg-zinc-900 ${
        side === "left"
          ? "border-r border-zinc-950/5 dark:border-white/10"
          : "border-l border-zinc-950/5 dark:border-white/10"
      } ${className}`}
      style={{ width }}
    >
      <ResizeHandle
        edge={side === "left" ? "right" : "left"}
        width={width}
        onWidth={onWidth}
        onReset={onReset}
      />
      {children}
    </div>
  );
}

function AppSidebar({
  theme,
  onToggleTheme,
}: {
  theme: Theme;
  onToggleTheme: () => void;
}) {
  const runtime = useRuntime();
  return (
    <Sidebar>
      <SidebarHeader>
        <img
          src="/wefabricate_Logo_Inline_Black.svg"
          alt="Wefabricate"
          className="h-8 w-auto self-start dark:invert"
        />
      </SidebarHeader>
      <SidebarBody>
        <SidebarSection>
          <SidebarHeading>Cells</SidebarHeading>
          <SidebarItem
            current={runtime.realm.kind === "cell"}
            href="#cell"
            onClick={(event: ReactMouseEvent<HTMLAnchorElement>) => {
              event.preventDefault();
              runtime.setRealm({ kind: "cell", replaySession: null });
            }}
          >
            <Cpu data-slot="icon" />
            <SidebarLabel>{CELL_NAME}</SidebarLabel>
            <span
              className={`ml-auto size-2 rounded-full ${
                runtime.driverAlive
                  ? "bg-emerald-500"
                  : "bg-zinc-300 dark:bg-zinc-600"
              }`}
              title={runtime.driverAlive ? "Driver alive" : "Driver down"}
            />
          </SidebarItem>
        </SidebarSection>
        <SidebarSection>
          <SidebarHeading>Recordings</SidebarHeading>
          {runtime.replaySessions.length === 0 ? (
            <div className="px-2 py-1 text-xs/5 text-zinc-500 dark:text-zinc-400">
              No replay sessions available
            </div>
          ) : (
            runtime.replaySessions.map((sid) => (
              <SidebarItem
                key={sid}
                current={
                  runtime.realm.kind === "replay" &&
                  runtime.realm.replaySession === sid
                }
                href={`#replay-${sid}`}
                onClick={(event: ReactMouseEvent<HTMLAnchorElement>) => {
                  event.preventDefault();
                  runtime.setRealm({ kind: "replay", replaySession: sid });
                }}
              >
                <Database data-slot="icon" />
                <SidebarLabel>{sid}</SidebarLabel>
              </SidebarItem>
            ))
          )}
        </SidebarSection>
        <SidebarSpacer />
      </SidebarBody>
      <SidebarFooter>
        <SidebarSection>
          <div className="space-y-2 px-2 pb-2 text-xs text-zinc-500 dark:text-zinc-400">
            <div className="flex items-center justify-between gap-3">
              <span>Bridge</span>
              <Badge color={runtime.wsConnected ? "emerald" : "red"}>
                {runtime.wsConnected ? "connected" : "offline"}
              </Badge>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span>Control</span>
              <Badge color={runtime.holdsControl ? "blue" : "zinc"}>
                {runtime.holdsControl ? "owned" : "released"}
              </Badge>
            </div>
          </div>
          <SidebarItem onClick={onToggleTheme}>
            {theme === "dark" ? (
              <Sun data-slot="icon" />
            ) : (
              <Moon data-slot="icon" />
            )}
            <SidebarLabel>
              {theme === "dark" ? "Light theme" : "Dark theme"}
            </SidebarLabel>
          </SidebarItem>
        </SidebarSection>
      </SidebarFooter>
    </Sidebar>
  );
}

function WorkspaceHeader({
  tool,
  onOpenScene,
}: {
  tool: WorkspaceTool;
  onOpenScene: () => void;
}) {
  const runtime = useRuntime();
  const owner = runtime.controlOwner?.owner ?? null;
  const resourceName =
    runtime.realm.kind === "cell"
      ? CELL_NAME
      : runtime.realm.replaySession ?? "Select recording";
  const toolLabel = TOOL_META.find((item) => item.id === tool)?.label ?? tool;

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b border-zinc-950/5 px-3 dark:border-white/10">
      <Button plain className="xl:hidden" onClick={onOpenScene} title="Open scene structure">
        <GitBranch data-slot="icon" />
      </Button>
      <div className="flex min-w-0 items-center gap-1.5 text-sm/6 text-zinc-500 dark:text-zinc-400">
        <span className="max-sm:hidden">
          {runtime.realm.kind === "cell" ? "Cells" : "Recordings"}
        </span>
        <ChevronRight className="size-4 shrink-0 max-sm:hidden" />
        <span className="truncate font-medium text-zinc-950 dark:text-white">
          {resourceName}
        </span>
      </div>
      <Badge color="zinc" className="max-md:hidden">
        {toolLabel}
      </Badge>
      <div className="ml-auto flex min-w-0 items-center gap-2">
        <Badge
          color={
            runtime.safetyActive
              ? "red"
              : runtime.status === null
                ? "zinc"
                : "emerald"
          }
        >
          {runtime.status?.estop
            ? "E-STOP"
            : runtime.status?.protective_stop
              ? "P-STOP"
              : runtime.status === null
                ? "NO STATUS"
                : "SAFE"}
        </Badge>
        <span className="hidden font-mono text-xs tabular-nums text-zinc-500 2xl:inline dark:text-zinc-400">
          speed {runtime.status === null ? "—" : `${Math.round(runtime.status.speed_scale * 100)}%`}
        </span>
        <Input
          value={runtime.url}
          spellCheck={false}
          aria-label="Zenoh WebSocket URL"
          className="hidden w-44 xl:block"
          onChange={(event) => runtime.setUrl(event.target.value)}
        />
        <Button
          outline
          disabled={runtime.connecting}
          onClick={() => void runtime.connect()}
          title={runtime.wsConnected ? "Reconnect to bridge" : "Connect to bridge"}
        >
          <Network data-slot="icon" />
          <span className="hidden 2xl:inline">
            {runtime.connecting
              ? "Connecting…"
              : runtime.wsConnected
                ? "Reconnect"
                : "Connect"}
          </span>
        </Button>
        <Button
          outline
          disabled={!runtime.commandsEnabled}
          onClick={runtime.holdsControl ? runtime.release : runtime.acquire}
          title={
            owner === null
              ? "Request control"
              : runtime.holdsControl
                ? "Release control"
                : `Held by ${owner.user}`
          }
        >
          <CircleGauge data-slot="icon" />
          <span className="hidden xl:inline">
            {runtime.holdsControl
              ? "Release"
              : owner === null
                ? "Request control"
                : owner.user}
          </span>
        </Button>
        <Button
          color="red"
          disabled={
            runtime.session === null ||
            runtime.prefix === null ||
            !runtime.commandsEnabled
          }
          onClick={() => {
            if (runtime.session !== null && runtime.prefix !== null) {
              void stop(runtime.session, runtime.prefix);
            }
          }}
        >
          <Square data-slot="icon" />
          <span className="max-sm:hidden">STOP</span>
        </Button>
      </div>
    </header>
  );
}

function RightToolPane({
  tool,
  structure,
  preview,
  onPreview,
  onConfigurationMutated,
}: {
  tool: WorkspaceTool;
  structure: SceneStructure;
  preview: ScenePreview;
  onPreview: (preview: ScenePreview) => void;
  onConfigurationMutated: () => void;
}) {
  const runtime = useRuntime();
  if (runtime.prefix === null) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm/6 text-zinc-500 dark:text-zinc-400">
        Select a recording from the main navigation.
      </div>
    );
  }
  const common = { session: runtime.session, realm: runtime.prefix };

  if (tool === "overview") {
    return (
      <div className="h-full space-y-2 overflow-y-auto p-2">
        <StatusPanel
          status={runtime.status}
          driverAlive={runtime.driverAlive}
          jointsCountRef={runtime.jointsCountRef}
          flangeRef={runtime.flangeRef}
          onClearProtectiveStop={() => {
            if (runtime.session === null || runtime.prefix === null) {
              return Promise.reject(new Error("not connected"));
            }
            return clearProtectiveStop(runtime.session, runtime.prefix);
          }}
        />
        <MotionPanel
          {...common}
          enabled={runtime.commandsEnabled}
          commandsEnabled={runtime.commandsEnabled}
          clientId={runtime.clientId}
          holdsControl={runtime.holdsControl}
          jointsRef={runtime.jointsRef}
          activeTcp={runtime.status?.active_tcp ?? null}
        />
      </div>
    );
  }
  if (tool === "operate") {
    return (
      <OperatePage
        {...common}
        clientId={runtime.clientId}
        holdsControl={runtime.holdsControl}
        ownerUser={runtime.controlOwner?.owner?.user ?? null}
        onAcquire={runtime.acquire}
        status={runtime.status}
        jointsRef={runtime.jointsRef}
        driverAlive={runtime.driverAlive}
        commandsEnabled={runtime.commandsEnabled}
      />
    );
  }
  if (tool === "io") {
    return (
      <IoPage
        {...common}
        io={runtime.io}
        wsConnected={runtime.wsConnected}
        commandsEnabled={runtime.commandsEnabled}
      />
    );
  }
  if (tool === "cameras") {
    return (
      <CamerasPage
        {...common}
        wsConnected={runtime.wsConnected}
        commandsEnabled={runtime.commandsEnabled}
      />
    );
  }
  if (tool === "topics") {
    return <TopicsPage session={runtime.session} wsConnected={runtime.wsConnected} compact />;
  }
  return (
    <div className="flex h-full min-h-0 flex-col">
      {runtime.realm.kind === "cell" && (
        <div className="shrink-0 border-b border-zinc-950/5 p-3 dark:border-white/10">
          <h2 className="mb-2 text-sm/6 font-semibold text-zinc-950 dark:text-white">
            Device sources
          </h2>
          <DeviceTree
            session={runtime.session}
            realm={runtime.prefix}
            commandsEnabled={runtime.commandsEnabled}
            devices={structure.devices}
          />
        </div>
      )}
      <div className="min-h-0 flex-1">
        <FramesPage
          key={`${structure.frames.length}:${structure.tcps.length}:${structure.poses.length}:${structure.objects.length}`}
          session={runtime.session}
          jointsRef={runtime.jointsRef}
          flangeRef={runtime.flangeRef}
          panelOnly
          structure={structure}
          onPreviewChange={onPreview}
          onConfigurationMutated={onConfigurationMutated}
        />
      </div>
      {preview !== null && (
        <div className="shrink-0 border-t border-zinc-950/5 px-3 py-2 text-xs/5 text-zinc-500 dark:border-white/10 dark:text-zinc-400">
          Previewing <span className="font-medium text-zinc-950 dark:text-white">{preview.name}</span> in the workspace
        </div>
      )}
    </div>
  );
}

function Workspace({
  theme,
  onToggleTheme,
}: {
  theme: Theme;
  onToggleTheme: () => void;
}) {
  const runtime = useRuntime();
  const [tool, setTool] = useState<WorkspaceTool>("overview");
  const [preview, setPreview] = useState<ScenePreview>(null);
  const [selection, setSelection] = useState<SceneSelection | null>(null);
  const [createRequest, setCreateRequest] =
    useState<SceneCreateRequest | null>(null);
  const [configurationRevision, setConfigurationRevision] = useState(0);
  const [sceneOpen, setSceneOpen] = useState(false);
  const [visibility, setVisibility] = useState<ViewerVisibility>(() => {
    const stored = localStorage.getItem("wf.viewer.visibility");
    if (stored === null) return DEFAULT_VIEWER_VISIBILITY;
    try {
      return {
        ...DEFAULT_VIEWER_VISIBILITY,
        ...(JSON.parse(stored) as Partial<ViewerVisibility>),
      };
    } catch {
      return DEFAULT_VIEWER_VISIBILITY;
    }
  });
  const [hiddenSceneItems, setHiddenSceneItems] = useState<Set<string>>(() => {
    const stored = localStorage.getItem("wf.viewer.hidden-scene-items");
    if (stored === null) return new Set();
    try {
      const values = JSON.parse(stored) as unknown;
      return Array.isArray(values)
        ? new Set(values.filter((value): value is string => typeof value === "string"))
        : new Set();
    } catch {
      return new Set();
    }
  });
  const [dragMode, setDragMode] = useState<TcpDragMode>("off");
  const [dragPending, setDragPending] = useState(false);
  const [dragError, setDragError] = useState<string | null>(null);
  const structure = useSceneStructure(
    runtime.session,
    runtime.prefix,
    configurationRevision,
  );
  const dragAllowed =
    runtime.commandsEnabled && runtime.driverAlive && runtime.holdsControl;
  const effectiveDragMode = dragAllowed ? dragMode : "off";
  const maxLeft = Math.max(280, Math.min(520, window.innerWidth - 80));
  const [leftWidth, setLeftWidth] = useRememberedWidth(
    "wf.shell.scene-width",
    LEFT_DEFAULT,
    260,
    maxLeft,
  );
  const navigationWidth = window.innerWidth >= 1024 ? 256 : 0;
  const dockedSceneWidth = window.innerWidth >= 1280 ? leftWidth : 0;
  const maxRight = Math.max(
    340,
    Math.min(
      760,
      window.innerWidth - navigationWidth - dockedSceneWidth - 400,
    ),
  );
  const [rightWidth, setRightWidth] = useRememberedWidth(
    `wf.shell.right-width.${tool}`,
    RIGHT_DEFAULT[tool],
    340,
    maxRight,
  );
  useEffect(() => {
    localStorage.setItem("wf.viewer.visibility", JSON.stringify(visibility));
  }, [visibility]);
  useEffect(() => {
    localStorage.setItem(
      "wf.viewer.hidden-scene-items",
      JSON.stringify([...hiddenSceneItems]),
    );
  }, [hiddenSceneItems]);

  const toggleSceneVisibility = (id: string) => {
    setHiddenSceneItems((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };


  const commitDraggedTcp = useCallback(
    async (
      xyz: [number, number, number],
      quat: [number, number, number, number],
    ) => {
      if (
        runtime.session === null ||
        runtime.prefix === null ||
        dragPending ||
        !dragAllowed
      ) {
        return;
      }
      setDragPending(true);
      setDragError(null);
      try {
        const handle = await sendExecutePath(
          runtime.session,
          runtime.prefix,
          [
            {
              type: "movej",
              target: {
                pose: { frame: "arm/r1/base", xyz, quat },
              },
              speed: null,
              accel: null,
              blend_radius: 0,
            },
          ],
          { clientId: runtime.clientId },
        );
        const result = await handle.result;
        if (result.state !== "succeeded") {
          setDragError(
            result.error === null
              ? result.state
              : `${result.state}: ${result.error}`,
          );
        }
      } catch (reason) {
        setDragError(
          reason instanceof Error ? reason.message : String(reason),
        );
      } finally {
        setDragPending(false);
      }
    },
    [
      dragAllowed,
      dragPending,
      runtime.clientId,
      runtime.prefix,
      runtime.session,
    ],
  );

  const chooseTool = (next: WorkspaceTool) => {
    setTool(next);
    setSelection(null);
    setCreateRequest(null);
    setDragMode("off");
    if (next !== "configuration") setPreview(null);
  };
  const mutateConfiguration = () => {
    setConfigurationRevision((revision) => revision + 1);
  };
  const groupForCreateKind = (kind: SceneCreateKind): SceneGroupKind =>
    kind === "frame"
      ? "frames"
      : kind === "tcp"
        ? "tcps"
        : kind === "pose"
          ? "poses"
          : "objects";
  const openCreate = (request: SceneCreateRequest) => {
    setDragMode("off");
    setCreateRequest(request);
    setSceneOpen(false);
  };
  const selectSceneItem = (next: SceneSelection) => {
    setDragMode("off");
    setCreateRequest(null);
    setSelection(next);
    setSceneOpen(false);
  };

  const hierarchy = (
    <SceneHierarchy
      structure={structure}
      selected={selection}
      hidden={hiddenSceneItems}
      onSelect={selectSceneItem}
      onCreate={openCreate}
      onToggleVisibility={toggleSceneVisibility}
    />
  );

  return (
    <SidebarLayout
      sidebar={<AppSidebar theme={theme} onToggleTheme={onToggleTheme} />}
      navbar={<Navbar><NavbarLabel>{CELL_NAME}</NavbarLabel></Navbar>}
    >
      <div
        data-realm={runtime.realm.kind}
        className={`flex h-full min-h-0 flex-col ${runtime.safetyActive ? "safety-active" : ""}`}
      >
        <WorkspaceHeader tool={tool} onOpenScene={() => setSceneOpen(true)} />
        <div className="workspace flex min-h-0 flex-1">
          <ResizablePane
            side="left"
            width={leftWidth}
            onWidth={setLeftWidth}
            onReset={() => setLeftWidth(LEFT_DEFAULT)}
            className="hidden xl:flex"
          >
            {hierarchy}
          </ResizablePane>

          <main className="relative min-w-0 flex-1 bg-zinc-100 dark:bg-zinc-950">
            <ToolRibbon
              active={tool}
              dragActive={effectiveDragMode !== "off"}
              dragAllowed={dragAllowed}
              dragPending={dragPending}
              onSelect={chooseTool}
              onToggleDrag={() => {
                setSelection(null);
                setCreateRequest(null);
                setDragError(null);
                setDragMode((current) =>
                  current === "off" ? "translate" : "off",
                );
              }}
            />
            {runtime.prefix === null ? (
              <div className="flex h-full items-center justify-center text-sm/6 text-zinc-500 dark:text-zinc-400">
                Select a recording from the main navigation.
              </div>
            ) : (
              <OverviewPage
                key={runtime.prefix}
                session={runtime.session}
                realm={runtime.prefix}
                jointsRef={runtime.jointsRef}
                jointsCountRef={runtime.jointsCountRef}
                flangeRef={runtime.flangeRef}
                status={runtime.status}
                driverAlive={runtime.driverAlive}
                commandsEnabled={runtime.commandsEnabled}
                clientId={runtime.clientId}
                holdsControl={runtime.holdsControl}
                workspace
                preview={preview}
                configurationRevision={configurationRevision}
                visibility={visibility}
                onVisibilityChange={setVisibility}
                hiddenSceneItems={hiddenSceneItems}
                dragMode={effectiveDragMode}
                dragPending={dragPending}
                onDragCommit={(xyz, quat) => void commitDraggedTcp(xyz, quat)}
              />
            )}
          </main>

          <ResizablePane
            side="right"
            width={rightWidth}
            onWidth={setRightWidth}
            onReset={() => setRightWidth(RIGHT_DEFAULT[tool])}
          >
            <aside className="h-full min-h-0 overflow-hidden bg-white dark:bg-zinc-900">
              {createRequest !== null ? (
                <SceneCreatePanel
                  key={`${createRequest.parent?.kind ?? "group"}:${createRequest.parent?.name ?? "root"}:${createRequest.kinds.join(",")}`}
                  request={createRequest}
                  structure={structure}
                  session={runtime.session}
                  jointsRef={runtime.jointsRef}
                  onSaved={(kind) => {
                    mutateConfiguration();
                    setCreateRequest(null);
                    setSelection({ kind: "group", name: groupForCreateKind(kind) });
                  }}
                  onClose={() => setCreateRequest(null)}
                />
              ) : selection?.kind === "group" ? (
                <SceneGroupTable
                  group={selection.name}
                  structure={structure}
                  onSelect={selectSceneItem}
                  onCreate={(kind) =>
                    openCreate({
                      kinds: [kind],
                      initialKind: kind,
                      parent: null,
                    })
                  }
                  onClose={() => setSelection(null)}
                />
              ) : selection !== null ? (
                <SceneDetails
                  selection={selection}
                  onClose={() => setSelection(null)}
                />
              ) : effectiveDragMode !== "off" ? (
                <TcpDragPanel
                  mode={effectiveDragMode}
                  allowed={dragAllowed}
                  pending={dragPending}
                  error={dragError}
                  activeTcp={runtime.status?.active_tcp ?? null}
                  onMode={setDragMode}
                  onClose={() => setDragMode("off")}
                />
              ) : (
                <RightToolPane
                  tool={tool}
                  structure={structure}
                  preview={preview}
                  onPreview={setPreview}
                  onConfigurationMutated={mutateConfiguration}
                />
              )}
            </aside>
          </ResizablePane>
        </div>

        {runtime.realm.kind === "replay" && (
          <ReplayDrawer
            key={runtime.realm.replaySession ?? ""}
            session={runtime.session}
            sid={runtime.realm.replaySession}
            sessions={runtime.replaySessions}
            onPickSession={(sid) =>
              runtime.setRealm({ kind: "replay", replaySession: sid })
            }
          />
        )}

        {sceneOpen && (
          <div className="fixed inset-0 z-50 xl:hidden">
            <button
              type="button"
              aria-label="Close scene structure"
              className="absolute inset-0 bg-black/30"
              onClick={() => setSceneOpen(false)}
            />
            <div className="absolute inset-y-2 left-2 w-[min(22rem,calc(100vw-1rem))] overflow-hidden rounded-xl bg-white shadow-2xl ring-1 ring-zinc-950/10 dark:bg-zinc-900 dark:ring-white/10">
              <Button
                plain
                className="absolute top-2 right-2 z-10"
                onClick={() => setSceneOpen(false)}
                title="Close scene structure"
              >
                <X data-slot="icon" />
              </Button>
              {hierarchy}
            </div>
          </div>
        )}
      </div>
    </SidebarLayout>
  );
}

export default function AppShell() {
  const [theme, setTheme] = useState<Theme>(() => {
    const stored = localStorage.getItem("wf.theme");
    return stored === "dark" ? "dark" : "light";
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("wf.theme", theme);
  }, [theme]);

  return (
    <Workspace
      theme={theme}
      onToggleTheme={() =>
        setTheme((current) => (current === "dark" ? "light" : "dark"))
      }
    />
  );
}
