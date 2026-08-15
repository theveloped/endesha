// Main navigation: cells, recordings, operator HMI, theme. Selection is a
// route change (the URL is the source of truth, see router.ts).
import { Cpu, Database, MonitorSmartphone, Moon, Sun } from "lucide-react";
import type { MouseEvent as ReactMouseEvent } from "react";
import { Badge } from "../catalyst/badge";
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
import { CELL_NAME } from "../lib/config";
import { useRuntime } from "../runtime/context";
import { routeToHash, type Route } from "./router";
import type { WorkspaceTool } from "./ToolRibbon";

export type Theme = "light" | "dark";

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
          <SidebarItem current={route.kind === "cell"} {...link({ kind: "cell", tool })}>
            <Cpu data-slot="icon" />
            <SidebarLabel>{CELL_NAME}</SidebarLabel>
            <span
              className={`ml-auto size-2 rounded-full ${
                runtime.driverAlive ? "bg-emerald-500" : "bg-zinc-300 dark:bg-zinc-600"
              }`}
              title={runtime.driverAlive ? "Driver alive" : "Driver down"}
            />
          </SidebarItem>
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
