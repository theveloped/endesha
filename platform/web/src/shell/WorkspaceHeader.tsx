// Workspace header: breadcrumb, safety badge, bridge URL/connect, control
// lease, STOP.
import { ChevronRight, CircleGauge, GitBranch, Network, Square } from "lucide-react";
import { Badge } from "../catalyst/badge";
import { Button } from "../catalyst/button";
import { Input } from "../catalyst/input";
import { stop } from "../lib/actions";
import { useRuntime } from "../runtime/context";
import { TOOL_META, type WorkspaceTool } from "./ToolRibbon";

export function WorkspaceHeader({
  tool,
  onOpenScene,
}: {
  tool: WorkspaceTool | "topics" | "program";
  onOpenScene?: () => void;
}) {
  const runtime = useRuntime();
  const owner = runtime.controlOwner?.owner ?? null;
  const resourceName =
    runtime.realm.kind === "cell"
      ? runtime.cellName
      : runtime.realm.replaySession ?? "Select recording";
  const toolLabel =
    tool === "topics"
      ? "Topics"
      : tool === "program"
        ? "Programs"
        : (TOOL_META.find((item) => item.id === tool)?.label ?? tool);

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b border-zinc-950/5 px-3 dark:border-white/10">
      {onOpenScene !== undefined && (
        <Button plain className="xl:hidden" onClick={onOpenScene} title="Open scene structure">
          <GitBranch data-slot="icon" />
        </Button>
      )}
      <div className="flex min-w-0 items-center gap-1.5 text-sm/6 text-zinc-500 dark:text-zinc-400">
        <span className="max-sm:hidden">
          {runtime.realm.kind === "cell" ? "Cells" : "Recordings"}
        </span>
        <ChevronRight className="size-4 shrink-0 max-sm:hidden" />
        <span className="truncate font-medium text-zinc-950 dark:text-white">{resourceName}</span>
      </div>
      <Badge color="zinc" className="max-md:hidden">
        {toolLabel}
      </Badge>
      <div className="ml-auto flex min-w-0 items-center gap-2">
        <Badge
          color={runtime.safetyActive ? "red" : runtime.status === null ? "zinc" : "emerald"}
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
            {runtime.connecting ? "Connecting…" : runtime.wsConnected ? "Reconnect" : "Connect"}
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
            {runtime.holdsControl ? "Release" : owner === null ? "Request control" : owner.user}
          </span>
        </Button>
        <Button
          color="red"
          disabled={runtime.session === null || runtime.prefix === null || !runtime.commandsEnabled}
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
