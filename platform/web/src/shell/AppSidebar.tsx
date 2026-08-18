// Main navigation: cells, recordings, operator HMI, theme. Selection is a
// route change (the URL is the source of truth, see router.ts).
import { Cpu, Database, MonitorSmartphone, Moon, Sun } from "lucide-react";
import { useState, type MouseEvent as ReactMouseEvent } from "react";
import { Badge } from "../catalyst/badge";
import { Button } from "../catalyst/button";
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
import type { HostCell } from "../lib/host";
import { useRuntime } from "../runtime/context";
import { routeToHash, type Route } from "./router";
import type { WorkspaceTool } from "./ToolRibbon";

export type Theme = "light" | "dark";

/** Inline "switch cell" panel: pick the overlay, confirm. Switching stops the
 * running cell's supervisor tree (programs, providers) — the host runs one
 * cell at a time on one bus. */
function SwitchCellPanel({
  cell,
  onConfirm,
  onCancel,
}: {
  cell: HostCell;
  onConfirm: (runtime: string | null) => Promise<void>;
  onCancel: () => void;
}) {
  const [runtime, setRuntime] = useState<string>(cell.runtimes.includes("default") ? "default" : (cell.runtimes[0] ?? ""));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <div className="mx-2 mb-1 rounded-lg border border-zinc-950/10 bg-zinc-50 p-2 text-xs dark:border-white/10 dark:bg-zinc-800/60">
      <div className="mb-1 font-medium text-zinc-950 dark:text-white">Switch to {cell.name}?</div>
      <p className="mb-2 text-zinc-500 dark:text-zinc-400">
        Stops the running cell (its programs and devices) and starts this one.
      </p>
      {cell.runtimes.length > 0 && (
        <label className="mb-2 flex items-center gap-2">
          <span className="text-zinc-500 dark:text-zinc-400">overlay</span>
          <select
            className="h-7 flex-1 rounded-md border border-zinc-950/10 bg-white px-1 font-mono text-xs dark:border-white/10 dark:bg-zinc-900"
            value={runtime}
            onChange={(ev) => setRuntime(ev.target.value)}
          >
            {cell.runtimes.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>
      )}
      <div className="flex gap-1">
        <Button
          color="blue"
          className="cmd"
          disabled={busy}
          onClick={() => {
            setBusy(true);
            setError(null);
            void onConfirm(runtime === "" ? null : runtime)
              .catch((e: unknown) => setError(e instanceof Error ? e.message : String(e)))
              .finally(() => setBusy(false));
          }}
        >
          {busy ? "Switching…" : "Switch"}
        </Button>
        <Button plain onClick={onCancel} disabled={busy}>Cancel</Button>
      </div>
      {error !== null && <p className="mt-1 text-red-600 dark:text-red-400">{error}</p>}
    </div>
  );
}

export function AppSidebar({
  route,
  tool,
  onNavigate,
  theme,
  onToggleTheme,
}: {
  route: Route;
  tool: WorkspaceTool;
  onNavigate: (route: Route) => void;
  theme: Theme;
  onToggleTheme: () => void;
}) {
  const runtime = useRuntime();
  const [switching, setSwitching] = useState<string | null>(null);
  const host = runtime.hostCells;
  const activeId = host?.active?.cell ?? null;
  const link = (target: Route) => ({
    href: routeToHash(target),
    onClick: (event: ReactMouseEvent<HTMLAnchorElement>) => {
      event.preventDefault();
      onNavigate(target);
    },
  });
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
          {host === null ? (
            <SidebarItem current={route.kind === "cell"} {...link({ kind: "cell", tool })}>
              <Cpu data-slot="icon" />
              <SidebarLabel>{runtime.cellName}</SidebarLabel>
              <span
                className={`ml-auto size-2 rounded-full ${runtime.driverAlive ? "bg-emerald-500" : "bg-zinc-300 dark:bg-zinc-600"}`}
                title={runtime.hostError ? `Host API unreachable: ${runtime.hostError}` : "Driver down"}
              />
            </SidebarItem>
          ) : (
            host.cells.map((cell) => {
              const isActive = cell.id === activeId;
              const item = isActive ? (
                <SidebarItem key={cell.id} current={route.kind === "cell"} {...link({ kind: "cell", tool })}>
                  <Cpu data-slot="icon" />
                  <SidebarLabel>{cell.name}</SidebarLabel>
                  <span
                    className={`ml-auto size-2 rounded-full ${host.alive ? "bg-emerald-500" : "bg-red-500"}`}
                    title={host.alive ? `Active (${host.active?.runtime ?? "no overlay"})` : "Active but its supervisor is down"}
                  />
                </SidebarItem>
              ) : (
                <SidebarItem
                  key={cell.id}
                  onClick={() => setSwitching((current) => (current === cell.id ? null : cell.id))}
                  title={cell.error ? `Broken cell.yaml: ${cell.error}` : `Switch to ${cell.name}`}
                >
                  <Cpu data-slot="icon" />
                  <SidebarLabel className={cell.error ? "line-through" : ""}>{cell.name}</SidebarLabel>
                  <span className="ml-auto size-2 rounded-full bg-zinc-300 dark:bg-zinc-600" title="Not running" />
                </SidebarItem>
              );
              return (
                <div key={cell.id}>
                  {item}
                  {switching === cell.id && cell.error === null && (
                    <SwitchCellPanel
                      cell={cell}
                      onConfirm={async (rt) => {
                        await runtime.activateCell(cell.id, rt);
                        setSwitching(null);
                        onNavigate({ kind: "cell", tool: "overview" });
                      }}
                      onCancel={() => setSwitching(null)}
                    />
                  )}
                </div>
              );
            })
          )}
          <SidebarItem current={route.kind === "hmi"} {...link({ kind: "hmi" })}>
            <MonitorSmartphone data-slot="icon" />
            <SidebarLabel>Operator HMI</SidebarLabel>
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
                current={route.kind === "replay" && route.sid === sid}
                {...link({ kind: "replay", sid, tool })}
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
            {theme === "dark" ? <Sun data-slot="icon" /> : <Moon data-slot="icon" />}
            <SidebarLabel>{theme === "dark" ? "Light theme" : "Dark theme"}</SidebarLabel>
          </SidebarItem>
        </SidebarSection>
      </SidebarFooter>
    </Sidebar>
  );
}
