// The engineering workspace shell. The URL (hash router) is the source of truth
// for realm + page/tool; the sidebar, header, panes and per-tool right pane live
// in their own modules. `#/cell/topics` and `#/cell/program` swap the pane trio
// for a full-page topic inspector / program studio; `#/cell/hmi` renders the
// operator page instead.
import { useCallback, useEffect, useState } from "react";
import { X } from "lucide-react";
import { Button } from "../catalyst/button";
import { Navbar, NavbarLabel } from "../catalyst/navbar";
import { SidebarLayout } from "../catalyst/sidebar-layout";
import ReplayDrawer from "../components/ReplayDrawer";
import { sendExecutePath } from "../lib/actions";
import HmiPage from "../pages/HmiPage";
import OverviewPage from "../pages/OverviewPage";
import LogsPage from "../pages/LogsPage";
import ProgramStudioPage from "../pages/ProgramStudioPage";
import QueriesPage from "../pages/QueriesPage";
import TopicsPage from "../pages/TopicsPage";
import { useRuntime } from "../runtime/context";
import { useProgram } from "../runtime/useProgram";
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
import { useSceneStructure } from "../scene/useSceneStructure";
import {
  DEFAULT_VIEWER_VISIBILITY,
  type TcpDragMode,
  type ViewerVisibility,
} from "../scene/viewerControls";
import { AppSidebar, type Theme } from "./AppSidebar";
import { RIGHT_DEFAULT_WIDTH, useRememberedWidth, useWindowWidth } from "./layout";
import { ResizablePane } from "./Panes";
import { RightToolPane } from "./RightToolPane";
import { useRoute, type Route } from "./router";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { WasherCard } from "../components/WasherCard";
import { ToolRibbon, type WorkspaceTool } from "./ToolRibbon";
import { WorkspaceHeader } from "./WorkspaceHeader";

const LEFT_DEFAULT = 300;

function NoArmWorkspace({
  devices,
  session,
  realm,
  clientId,
  canCommand,
}: {
  devices: { id: string; contract: string; active: string | null }[];
  session: Session | null;
  realm: string;
  clientId: string;
  canCommand: boolean;
}) {
  const washers = devices.filter((d) => d.contract === "washer");
  if (washers.length > 0) {
    return (
      <div className="h-full overflow-auto p-6">
        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          {washers.map((w) => (
            <WasherCard
              key={w.id}
              session={session}
              realm={realm}
              rid={w.id}
              active={w.active}
              clientId={clientId}
              canCommand={canCommand}
              showRecipe
            />
          ))}
          <p className="text-xs text-zinc-500 dark:text-zinc-400">
            The machine's raw PLC variables are on the IO tool ({devices.filter((d) => d.contract === "tags").map((d) => d.id).join(", ") || "no tags device"}).
          </p>
        </div>
      </div>
    );
  }
  return (
    <div className="flex h-full items-center justify-center p-8">
      <div className="max-w-md rounded-xl bg-white p-6 text-sm shadow-sm ring-1 ring-zinc-950/5 dark:bg-zinc-900 dark:ring-white/10">
        <h2 className="mb-1 font-semibold text-zinc-950 dark:text-white">No arm in this cell</h2>
        <p className="mb-3 text-zinc-500 dark:text-zinc-400">
          The 3D viewport shows an arm's digital twin. This cell has {devices.length} device
          {devices.length === 1 ? "" : "s"}; use the IO and Programs tools on the right.
        </p>
        <ul className="space-y-1 font-mono text-xs">
          {devices.map((d) => (
            <li key={d.id}>
              {d.id} <span className="text-zinc-500">{d.contract} · {d.active ?? "off"}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function Workspace({
  route,
  tool,
  navigate,
  theme,
  onToggleTheme,
}: {
  route: Route;
  tool: WorkspaceTool;
  navigate: (route: Route) => void;
  theme: Theme;
  onToggleTheme: () => void;
}) {
  const runtime = useRuntime();
  const [preview, setPreview] = useState<ScenePreview>(null);
  const [selection, setSelection] = useState<SceneSelection | null>(null);
  const [createRequest, setCreateRequest] = useState<SceneCreateRequest | null>(null);
  const [configurationRevision, setConfigurationRevision] = useState(0);
  const [sceneOpen, setSceneOpen] = useState(false);
  const [visibility, setVisibility] = useState<ViewerVisibility>(() => {
    const stored = localStorage.getItem("wf.viewer.visibility");
    if (stored === null) return DEFAULT_VIEWER_VISIBILITY;
    try {
      return { ...DEFAULT_VIEWER_VISIBILITY, ...(JSON.parse(stored) as Partial<ViewerVisibility>) };
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
  const isTopics = route.kind === "topics";
  const isProgram = route.kind === "program";
  // Full pages replace the workspace pane trio entirely.
  const fullPage =
    isTopics || isProgram || route.kind === "logs" || route.kind === "queries" ? route.kind : null;
  const structure = useSceneStructure(runtime.session, runtime.prefix, configurationRevision);
  const program = useProgram(runtime.session, runtime.prefix);
  const dragAllowed = runtime.commandsEnabled && runtime.driverAlive && runtime.holdsControl;
  const effectiveDragMode = dragAllowed ? dragMode : "off";

  const windowWidth = useWindowWidth();
  const maxLeft = Math.max(280, Math.min(520, windowWidth - 80));
  const [leftWidth, setLeftWidth] = useRememberedWidth("wf.shell.scene-width", LEFT_DEFAULT, 260, maxLeft);
  const navigationWidth = windowWidth >= 1024 ? 256 : 0;
  const dockedSceneWidth = windowWidth >= 1280 ? leftWidth : 0;
  const maxRight = Math.max(340, Math.min(760, windowWidth - navigationWidth - dockedSceneWidth - 400));
  const [rightWidth, setRightWidth] = useRememberedWidth(
    `wf.shell.right-width.${tool}`,
    RIGHT_DEFAULT_WIDTH[tool],
    340,
    maxRight,
  );

  useEffect(() => {
    localStorage.setItem("wf.viewer.visibility", JSON.stringify(visibility));
  }, [visibility]);
  useEffect(() => {
    localStorage.setItem("wf.viewer.hidden-scene-items", JSON.stringify([...hiddenSceneItems]));
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
    async (xyz: [number, number, number], quat: [number, number, number, number]) => {
      if (runtime.session === null || runtime.prefix === null || dragPending || !dragAllowed) return;
      setDragPending(true);
      setDragError(null);
      try {
        const handle = await sendExecutePath(
          runtime.session,
          runtime.prefix,
          [{ type: "movej", target: { pose: { frame: "arm/r1/base", xyz, quat } }, speed: null, accel: null, blend_radius: 0 }],
          { clientId: runtime.clientId },
        );
        const result = await handle.result;
        if (result.state !== "succeeded") {
          setDragError(result.error === null ? result.state : `${result.state}: ${result.error}`);
        }
      } catch (reason) {
        setDragError(reason instanceof Error ? reason.message : String(reason));
      } finally {
        setDragPending(false);
      }
    },
    [dragAllowed, dragPending, runtime.clientId, runtime.prefix, runtime.session],
  );

  const chooseTool = (next: WorkspaceTool) => {
    setSelection(null);
    setCreateRequest(null);
    if (next !== "configuration") setPreview(null);
    navigate(route.kind === "replay" ? { kind: "replay", sid: route.sid, tool: next } : { kind: "cell", tool: next });
  };
  const mutateConfiguration = () => setConfigurationRevision((revision) => revision + 1);
  const groupForCreateKind = (kind: SceneCreateKind): SceneGroupKind =>
    kind === "frame" ? "frames" : kind === "tcp" ? "tcps" : kind === "pose" ? "poses" : "objects";
  const openCreate = (request: SceneCreateRequest) => {
    setCreateRequest(request);
    setSceneOpen(false);
  };
  const selectSceneItem = (next: SceneSelection) => {
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

  const hasArm = structure.devices.length === 0 || structure.devices.some((d) => d.contract === "arm");
  const paneCtx =
    runtime.prefix === null
      ? null
      : {
          runtime,
          prefix: runtime.prefix,
          structure,
          program,
          preview,
          onPreview: setPreview,
          onConfigurationMutated: mutateConfiguration,
          // Editing happens on the full program studio page.
          onEditProgram: (name: string | null) => navigate({ kind: "program", name }),
        };

  return (
    <SidebarLayout
      sidebar={<AppSidebar route={route} tool={tool} onNavigate={navigate} theme={theme} onToggleTheme={onToggleTheme} />}
      navbar={<Navbar><NavbarLabel>{runtime.cellName}</NavbarLabel></Navbar>}
    >
      <div
        data-realm={runtime.realm.kind}
        className={`flex h-full min-h-0 flex-col ${runtime.safetyActive ? "safety-active" : ""}`}
      >
        <WorkspaceHeader
          tool={fullPage ?? tool}
          onOpenScene={fullPage !== null ? undefined : () => setSceneOpen(true)}
        />
        {isTopics ? (
          <main className="min-h-0 min-w-0 flex-1 overflow-hidden">
            <TopicsPage session={runtime.session} wsConnected={runtime.wsConnected} />
          </main>
        ) : fullPage === "logs" || fullPage === "queries" ? (
          <main className="min-h-0 min-w-0 flex-1 overflow-hidden">
            {runtime.prefix === null ? (
              <div className="flex h-full items-center justify-center text-sm/6 text-zinc-500 dark:text-zinc-400">
                Connect to a cell first.
              </div>
            ) : fullPage === "logs" ? (
              <LogsPage session={runtime.session} realm={runtime.prefix} wsConnected={runtime.wsConnected} />
            ) : (
              <QueriesPage session={runtime.session} realm={runtime.prefix} wsConnected={runtime.wsConnected} />
            )}
          </main>
        ) : isProgram ? (
          <main className="min-h-0 min-w-0 flex-1 overflow-hidden">
            {runtime.prefix === null ? (
              <div className="flex h-full items-center justify-center text-sm/6 text-zinc-500 dark:text-zinc-400">
                Connect to a cell to edit its programs.
              </div>
            ) : (
              <ProgramStudioPage
                session={runtime.session}
                realm={runtime.prefix}
                program={program}
                theme={theme}
                initialName={route.kind === "program" ? route.name : null}
              />
            )}
          </main>
        ) : (
        <div className="workspace flex min-h-0 flex-1">
          <ResizablePane
            side="left"
            width={leftWidth}
            onWidth={setLeftWidth}
            onReset={() => setLeftWidth(LEFT_DEFAULT)}
            className="hidden xl:block"
          >
            {hierarchy}
          </ResizablePane>

          <main className="relative min-w-0 flex-1 bg-zinc-100 dark:bg-zinc-950">
            <ToolRibbon
              active={tool}
              dragMode={effectiveDragMode}
              dragAllowed={dragAllowed}
              dragPending={dragPending}
              onSelect={chooseTool}
              onDragMode={(mode) => {
                setDragError(null);
                setDragMode(mode);
              }}
            />
            {dragError !== null && (
              <div className="absolute top-14 left-1/2 z-20 flex max-w-md -translate-x-1/2 items-start gap-2 rounded-lg bg-red-50/95 px-3 py-2 text-xs/5 text-red-700 shadow-lg ring-1 ring-red-500/20 backdrop-blur dark:bg-red-950/80 dark:text-red-300">
                <p className="min-w-0 break-words">{dragError}</p>
                <button
                  type="button"
                  aria-label="Dismiss drag error"
                  className="shrink-0 rounded p-0.5 hover:bg-red-500/10"
                  onClick={() => setDragError(null)}
                >
                  <X className="size-3.5" />
                </button>
              </div>
            )}
            {runtime.prefix === null ? (
              <div className="flex h-full items-center justify-center text-sm/6 text-zinc-500 dark:text-zinc-400">
                Select a recording from the main navigation.
              </div>
            ) : !hasArm ? (
              <NoArmWorkspace
                devices={structure.devices}
                session={runtime.session}
                realm={runtime.prefix}
                clientId={runtime.clientId}
                canCommand={runtime.commandsEnabled && runtime.holdsControl}
              />
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
            onReset={() => setRightWidth(RIGHT_DEFAULT_WIDTH[tool])}
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
                  onCreate={(kind) => openCreate({ kinds: [kind], initialKind: kind, parent: null })}
                  onClose={() => setSelection(null)}
                />
              ) : selection !== null ? (
                <SceneDetails selection={selection} onClose={() => setSelection(null)} />
              ) : (
                <RightToolPane tool={tool} ctx={paneCtx} />
              )}
            </aside>
          </ResizablePane>
        </div>
        )}

        {runtime.realm.kind === "replay" && (
          <ReplayDrawer
            key={runtime.realm.replaySession ?? ""}
            session={runtime.session}
            sid={runtime.realm.replaySession}
            sessions={runtime.replaySessions}
            onPickSession={(sid) => navigate({ kind: "replay", sid, tool })}
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
              <Button plain className="absolute top-2 right-2 z-10" onClick={() => setSceneOpen(false)} title="Close scene structure">
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
  const runtime = useRuntime();
  const [route, navigate] = useRoute();
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem("wf.theme") === "dark" ? "dark" : "light"));
  // Last workspace tool, so the full-page views (HMI, Topics) hand back to it.
  // Adjusted during render (not in an effect): it derives from the route.
  const [lastTool, setLastTool] = useState<WorkspaceTool>("overview");
  if ((route.kind === "cell" || route.kind === "replay") && route.tool !== lastTool) {
    setLastTool(route.tool);
  }

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("wf.theme", theme);
  }, [theme]);

  // The route drives the realm; Topics and the HMI belong to the active cell.
  const { setRealm } = runtime;
  useEffect(() => {
    if (route.kind === "replay") {
      setRealm({ kind: "replay", replaySession: route.sid });
    } else {
      setRealm({ kind: "cell", replaySession: null });
    }
  }, [route, setRealm]);

  const toggleTheme = () => setTheme((current) => (current === "dark" ? "light" : "dark"));

  if (route.kind === "hmi") {
    return <HmiPage onExit={() => navigate({ kind: "cell", tool: lastTool })} />;
  }
  return (
    <Workspace
      route={route}
      tool={route.kind === "cell" || route.kind === "replay" ? route.tool : lastTool}
      navigate={navigate}
      theme={theme}
      onToggleTheme={toggleTheme}
    />
  );
}
