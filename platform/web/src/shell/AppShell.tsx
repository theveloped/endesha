import {
  useCallback,
  useEffect,
  useState,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";
import {
  Activity,
  Camera,
  ChevronRight,
  CircleGauge,
  Cpu,
  Database,
  Hand,
  Moon,
  Network,
  RadioTower,
  SlidersHorizontal,
  Square,
  Sun,
  Waypoints,
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
import StatusPanel from "../components/StatusPanel";
import CamerasPage from "../pages/CamerasPage";
import FramesPage from "../pages/FramesPage";
import IoPage from "../pages/IoPage";
import OperatePage from "../pages/OperatePage";
import OverviewPage from "../pages/OverviewPage";
import TopicsPage from "../pages/TopicsPage";
import { clearProtectiveStop, stop } from "../lib/actions";
import { CELL_NAME } from "../lib/config";
import { useRuntime } from "../runtime/context";
import type { ScenePreview } from "../scene/types";

export type WorkspaceSection =
  | "overview"
  | "operate"
  | "io"
  | "cameras"
  | "configuration"
  | "topics";

type Theme = "light" | "dark";

const SECTIONS: Array<{
  id: WorkspaceSection;
  label: string;
  description: string;
  icon: typeof Activity;
}> = [
  {
    id: "overview",
    label: "Overview",
    description: "Cell status and engineering motion",
    icon: Activity,
  },
  {
    id: "operate",
    label: "Operate",
    description: "Joint and Cartesian jogging",
    icon: Hand,
  },
  {
    id: "io",
    label: "IO",
    description: "Digital and analog signals",
    icon: SlidersHorizontal,
  },
  {
    id: "cameras",
    label: "Cameras",
    description: "Images and acquisition",
    icon: Camera,
  },
  {
    id: "configuration",
    label: "Configuration",
    description: "Frames, TCPs, poses and device sources",
    icon: Waypoints,
  },
  {
    id: "topics",
    label: "Topics",
    description: "Raw Zenoh samples and metadata",
    icon: RadioTower,
  },
];

const LEFT_DEFAULT: Record<WorkspaceSection, number> = {
  overview: 288,
  operate: 288,
  io: 288,
  cameras: 288,
  configuration: 520,
  topics: 288,
};

const RIGHT_DEFAULT: Record<
  Exclude<WorkspaceSection, "configuration" | "topics">,
  number
> = {
  overview: 360,
  operate: 560,
  io: 540,
  cameras: 620,
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
  section,
  onSection,
  theme,
  onToggleTheme,
}: {
  section: WorkspaceSection;
  onSection: (section: WorkspaceSection) => void;
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
          {SECTIONS.map((item) => {
            const Icon = item.icon;
            return (
              <SidebarItem
                key={item.id}
                current={section === item.id}
                href={`#${item.id}`}
                onClick={(event: ReactMouseEvent<HTMLAnchorElement>) => {
                  event.preventDefault();
                  onSection(item.id);
                }}
              >
                <Icon data-slot="icon" />
                <SidebarLabel>{item.label}</SidebarLabel>
              </SidebarItem>
            );
          })}
        </SidebarSection>

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
                runtime.driverAlive ? "bg-emerald-500" : "bg-zinc-300 dark:bg-zinc-600"
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

function WorkspaceHeader({ section }: { section: WorkspaceSection }) {
  const runtime = useRuntime();
  const item = SECTIONS.find((entry) => entry.id === section)!;
  const owner = runtime.controlOwner?.owner ?? null;
  const resourceName =
    runtime.realm.kind === "cell"
      ? CELL_NAME
      : runtime.realm.replaySession ?? "Select recording";

  return (
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-zinc-950/5 px-4 dark:border-white/10">
      <div className="flex min-w-0 items-center gap-1.5 text-sm/6 text-zinc-500 dark:text-zinc-400">
        <span>{runtime.realm.kind === "cell" ? "Cells" : "Recordings"}</span>
        <ChevronRight className="size-4 shrink-0" />
        <span className="truncate font-medium text-zinc-950 dark:text-white">
          {resourceName}
        </span>
      </div>
      <Badge color="zinc" className="max-sm:hidden">
        {item.label}
      </Badge>

      <div className="ml-auto flex items-center gap-2">
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
        <span className="hidden font-mono text-xs tabular-nums text-zinc-500 xl:inline dark:text-zinc-400">
          speed {runtime.status === null ? "—" : `${Math.round(runtime.status.speed_scale * 100)}%`}
        </span>
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
          STOP
        </Button>
      </div>
    </header>
  );
}

function SectionIntro({ section }: { section: WorkspaceSection }) {
  const item = SECTIONS.find((entry) => entry.id === section)!;
  const Icon = item.icon;
  return (
    <div className="border-b border-zinc-950/5 px-4 py-3 dark:border-white/10">
      <div className="flex items-center gap-2">
        <Icon className="size-4 text-zinc-500 dark:text-zinc-400" />
        <h2 className="text-sm/6 font-semibold text-zinc-950 dark:text-white">
          {item.label}
        </h2>
      </div>
      <p className="mt-0.5 text-xs/5 text-zinc-500 dark:text-zinc-400">
        {item.description}
      </p>
    </div>
  );
}

function ConnectionPanel() {
  const runtime = useRuntime();
  return (
    <section className="space-y-2">
      <h3 className="text-xs/6 font-medium text-zinc-500 dark:text-zinc-400">
        Connection
      </h3>
      <Input
        value={runtime.url}
        spellCheck={false}
        aria-label="Zenoh WebSocket URL"
        onChange={(event) => runtime.setUrl(event.target.value)}
      />
      <Button
        color="blue"
        className="w-full"
        disabled={runtime.connecting}
        onClick={() => void runtime.connect()}
      >
        <Network data-slot="icon" />
        {runtime.connecting
          ? "Connecting…"
          : runtime.wsConnected
            ? "Reconnect"
            : "Connect"}
      </Button>
      {runtime.connectError !== null && (
        <p className="text-xs/5 text-red-600 dark:text-red-400">
          {runtime.connectError}
        </p>
      )}
    </section>
  );
}

function LeftRail({
  section,
  onPreview,
  onConfigurationMutated,
}: {
  section: WorkspaceSection;
  onPreview: (preview: ScenePreview) => void;
  onConfigurationMutated: () => void;
}) {
  const runtime = useRuntime();

  return (
    <aside className="flex h-full min-h-0 flex-col">
      <SectionIntro section={section} />
      <div className="min-h-0 flex-1 overflow-y-auto">
        {section === "configuration" ? (
          <>
            <div className="space-y-5 border-b border-zinc-950/5 p-4 dark:border-white/10">
              <ConnectionPanel />
              {runtime.prefix !== null && runtime.realm.kind === "cell" && (
                <section className="space-y-2">
                  <h3 className="text-xs/6 font-medium text-zinc-500 dark:text-zinc-400">
                    Device sources
                  </h3>
                  <DeviceTree
                    session={runtime.session}
                    realm={runtime.prefix}
                    commandsEnabled={runtime.commandsEnabled}
                  />
                </section>
              )}
            </div>
            <FramesPage
              session={runtime.session}
              jointsRef={runtime.jointsRef}
              flangeRef={runtime.flangeRef}
              panelOnly
              onPreviewChange={onPreview}
              onConfigurationMutated={onConfigurationMutated}
            />
          </>
        ) : (
          <div className="space-y-5 p-4">
            <ConnectionPanel />
            {runtime.prefix === null ? (
              <p className="rounded-lg bg-zinc-950/2.5 p-3 text-sm/6 text-zinc-500 dark:bg-white/5 dark:text-zinc-400">
                Select a recording from the main navigation.
              </p>
            ) : runtime.realm.kind === "cell" &&
              (section === "overview" || section === "cameras") ? (
              <section className="space-y-2">
                <h3 className="text-xs/6 font-medium text-zinc-500 dark:text-zinc-400">
                  Device sources
                </h3>
                <DeviceTree
                  session={runtime.session}
                  realm={runtime.prefix}
                  commandsEnabled={runtime.commandsEnabled}
                />
              </section>
            ) : section === "operate" ? (
              <div className="space-y-2 text-sm/6 text-zinc-600 dark:text-zinc-300">
                <p>Jog the active TCP in joint or Cartesian coordinates.</p>
                <p className="rounded-lg bg-amber-500/10 p-3 text-xs/5 text-amber-800 ring-1 ring-amber-500/20 dark:text-amber-300">
                  Continuous jog stops on pointer release. The driver watchdog remains authoritative.
                </p>
              </div>
            ) : section === "io" ? (
              <div className="grid grid-cols-2 gap-2 text-center text-xs/5 text-zinc-500 dark:text-zinc-400">
                <div className="rounded-lg bg-zinc-950/2.5 p-3 ring-1 ring-zinc-950/5 dark:bg-white/5 dark:ring-white/10">
                  <strong className="block text-sm text-zinc-950 dark:text-white">16</strong>
                  digital inputs
                </div>
                <div className="rounded-lg bg-zinc-950/2.5 p-3 ring-1 ring-zinc-950/5 dark:bg-white/5 dark:ring-white/10">
                  <strong className="block text-sm text-zinc-950 dark:text-white">16</strong>
                  digital outputs
                </div>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </aside>
  );
}

function RightRail({ section }: { section: WorkspaceSection }) {
  const runtime = useRuntime();
  if (runtime.prefix === null) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm/6 text-zinc-500 dark:text-zinc-400">
        Select a recording from the main navigation.
      </div>
    );
  }
  const common = { session: runtime.session, realm: runtime.prefix };

  return (
    <aside className="h-full min-h-0 overflow-hidden bg-white dark:bg-zinc-900">
      {section === "overview" && (
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
      )}
      {section === "operate" && (
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
      )}
      {section === "io" && (
        <IoPage
          {...common}
          io={runtime.io}
          wsConnected={runtime.wsConnected}
          commandsEnabled={runtime.commandsEnabled}
        />
      )}
      {section === "cameras" && (
        <CamerasPage
          {...common}
          wsConnected={runtime.wsConnected}
          commandsEnabled={runtime.commandsEnabled}
        />
      )}
    </aside>
  );
}

function Workspace({ theme, onToggleTheme }: { theme: Theme; onToggleTheme: () => void }) {
  const runtime = useRuntime();
  const [section, setSection] = useState<WorkspaceSection>("overview");
  const [preview, setPreview] = useState<ScenePreview>(null);
  const [configurationRevision, setConfigurationRevision] = useState(0);
  const maxLeft = Math.max(280, Math.min(560, window.innerWidth - 40));
  const [leftWidth, setLeftWidth] = useRememberedWidth(
    `wf.shell.left-width.${section}`,
    LEFT_DEFAULT[section],
    240,
    maxLeft,
  );
  const rightSection =
    section === "configuration" || section === "topics" ? null : section;
  const maxRight = Math.max(360, Math.min(680, window.innerWidth - 540));
  const rightDefault = rightSection === null ? 360 : RIGHT_DEFAULT[rightSection];
  const [rightWidth, setRightWidth] = useRememberedWidth(
    `wf.shell.right-width.${section}`,
    rightDefault,
    320,
    maxRight,
  );

  const chooseSection = (next: WorkspaceSection) => {
    setSection(next);
    if (next !== "configuration") setPreview(null);
  };

  return (
    <SidebarLayout
      sidebar={
        <AppSidebar
          section={section}
          onSection={chooseSection}
          theme={theme}
          onToggleTheme={onToggleTheme}
        />
      }
      navbar={
        <Navbar>
          <NavbarLabel>
            {SECTIONS.find((item) => item.id === section)?.label}
          </NavbarLabel>
        </Navbar>
      }
    >
      <div
        data-realm={runtime.realm.kind}
        className={`flex h-full min-h-0 flex-col ${runtime.safetyActive ? "safety-active" : ""}`}
      >
        <WorkspaceHeader section={section} />
        {section === "topics" ? (
          <main className="min-h-0 flex-1">
            <TopicsPage
              session={runtime.session}
              wsConnected={runtime.wsConnected}
            />
          </main>
        ) : (
          <div className="workspace flex min-h-0 flex-1">
            <ResizablePane
              side="left"
              width={leftWidth}
              onWidth={setLeftWidth}
              onReset={() => setLeftWidth(LEFT_DEFAULT[section])}
              className={
                section === "configuration" ? "flex" : "hidden lg:flex"
              }
            >
              <LeftRail
                section={section}
                onPreview={setPreview}
                onConfigurationMutated={() =>
                  setConfigurationRevision((revision) => revision + 1)
                }
              />
            </ResizablePane>

            <main className="relative min-w-0 flex-1 bg-zinc-100 dark:bg-zinc-950">
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
                />
              )}
            </main>

          {rightSection !== null && (
            <ResizablePane
              side="right"
              width={rightWidth}
              onWidth={setRightWidth}
              onReset={() => setRightWidth(RIGHT_DEFAULT[rightSection])}
            >
              <RightRail section={rightSection} />
            </ResizablePane>
          )}
          </div>
        )}

        {section !== "topics" && runtime.realm.kind === "replay" && (
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
