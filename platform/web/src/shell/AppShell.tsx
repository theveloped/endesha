// The engineering workspace shell. The URL (hash router) is the source of truth
// for realm + tool; the sidebar, header, panes and per-tool right pane live in
// their own modules. `#/hmi` renders the operator page instead.
import { useCallback, useEffect, useRef, useState } from "react";
import { X } from "lucide-react";
import { Button } from "../catalyst/button";
import { Navbar, NavbarLabel } from "../catalyst/navbar";
import { SidebarLayout } from "../catalyst/sidebar-layout";
import ReplayDrawer from "../components/ReplayDrawer";
import { TcpDragPanel } from "../components/TcpDragPanel";
import { sendExecutePath } from "../lib/actions";
import HmiPage from "../pages/HmiPage";
import OverviewPage from "../pages/OverviewPage";
import ProgramEditorPane from "../pages/ProgramEditorPane";
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
  // Program editor mode: {open, program to open first}. Takes over the right pane.
  const [editor, setEditor] = useState<{ open: boolean; name: string | null }>({ open: false, name: null });
  const structure = useSceneStructure(runtime.session, runtime.prefix, configurationRevision);
  const program = useProgram(runtime.session, runtime.prefix);
  const dragAllowed = runtime.commandsEnabled && runtime.driverAlive && runtime.holdsControl;
  const effectiveDragMode = dragAllowed ? dragMode : "off";

  const windowWidth = useWindowWidth();
  const maxLeft = Math.max(280, Math.min(520, windowWidth - 80));
  const [leftWidth, setLeftWidth] = useRememberedWidth("wf.shell.scene-width", LEFT_DEFAULT, 260, maxLeft);
  const navigationWidth = windowWidth >= 1024 ? 256 : 0;
  const dockedSceneWidth = windowWidth >= 1280 ? leftWidth : 0;
  const maxRight = Math.max(340, Math.min(editor.open ? 1200 : 760, windowWidth - navigationWidth - dockedSceneWidth - 400));
  const [rightWidth, setRightWidth] = useRememberedWidth(
    editor.open ? "wf.shell.right-width.editor" : `wf.shell.right-width.${tool}`,
    editor.open ? 900 : RIGHT_DEFAULT_WIDTH[tool],
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
    setDragMode("off");
    if (next !== "programs") setEditor({ open: false, name: null });
    if (next !== "configuration") setPreview(null);
    navigate(route.kind === "replay" ? { kind: "replay", sid: route.sid, tool: next } : { kind: "cell", tool: next });
  };
  const mutateConfiguration = () => setConfigurationRevision((revision) => revision + 1);
  const groupForCreateKind = (kind: SceneCreateKind): SceneGroupKind =>
    kind === "frame" ? "frames" : kind === "tcp" ? "tcps" : kind === "pose" ? "poses" : "objects";
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
          onEditProgram: (name: string | null) => {
            setSelection(null);
            setCreateRequest(null);
            setDragMode("off");
            setEditor({ open: true, name });
          },
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
                setDragMode((current) => (current === "off" ? "translate" : "off"));
              }}
            />
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
            onReset={() => setRightWidth(editor.open ? 900 : RIGHT_DEFAULT_WIDTH[tool])}
          >
            <aside className="h-full min-h-0 overflow-hidden bg-white dark:bg-zinc-900">
              {editor.open && runtime.prefix !== null ? (
                <ProgramEditorPane
                  session={runtime.session}
                  realm={runtime.prefix}
                  program={program}
                  theme={theme}
                  initialName={editor.name}
                  onClose={() => setEditor({ open: false, name: null })}
                />
              ) : createRequest !== null ? (
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
                <RightToolPane tool={tool} ctx={paneCtx} />
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
  // Last workspace tool, so the HMI can hand back to it (a ref: no re-render).
  const lastTool = useRef<WorkspaceTool>("overview");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("wf.theme", theme);
  }, [theme]);

  // The route drives the realm; the workspace remembers the last tool so the
  // HMI can hand back to it.
  const { setRealm } = runtime;
  useEffect(() => {
    if (route.kind === "cell") {
      lastTool.current = route.tool;
      setRealm({ kind: "cell", replaySession: null });
    } else if (route.kind === "replay") {
      lastTool.current = route.tool;
      setRealm({ kind: "replay", replaySession: route.sid });
    }
  }, [route, setRealm]);

  const toggleTheme = () => setTheme((current) => (current === "dark" ? "light" : "dark"));

  if (route.kind === "hmi") {
    return <HmiPage onExit={() => navigate({ kind: "cell", tool: lastTool.current })} />;
  }
  return (
    <Workspace
      route={route}
      tool={route.tool}
      navigate={navigate}
      theme={theme}
      onToggleTheme={toggleTheme}
    />
  );
}
