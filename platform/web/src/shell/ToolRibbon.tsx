import {
  Activity,
  Camera,
  Hand,
  ListChecks,
  Move3d,
  Rotate3d,
  Settings2,
  SlidersHorizontal,
} from "lucide-react";
import type { TcpDragMode } from "../scene/viewerControls";

export type WorkspaceTool =
  | "overview"
  | "operate"
  | "programs"
  | "io"
  | "cameras"
  | "configuration";

const TOOLS: Array<{
  id: WorkspaceTool;
  label: string;
  hint: string;
  icon: typeof Activity;
}> = [
  { id: "overview", label: "Overview", hint: "Cell status and engineering motion", icon: Activity },
  { id: "operate", label: "Operate", hint: "Joint and Cartesian jogging", icon: Hand },
  { id: "programs", label: "Programs", hint: "Load and run programs (PackML unit)", icon: ListChecks },
  { id: "io", label: "IO", hint: "Digital and analog signals", icon: SlidersHorizontal },
  { id: "cameras", label: "Cameras", hint: "Images and acquisition", icon: Camera },
  { id: "configuration", label: "Configure", hint: "Frames, TCPs, poses and device sources", icon: Settings2 },
];

export const TOOL_META = TOOLS;

const DRAG_MODES: Array<{
  mode: Exclude<TcpDragMode, "off">;
  label: string;
  hint: string;
  icon: typeof Move3d;
}> = [
  { mode: "translate", label: "Drag TCP (translate)", hint: "Drag the active TCP with translation handles", icon: Move3d },
  { mode: "rotate", label: "Drag TCP (rotate)", hint: "Drag the active TCP with rotation handles", icon: Rotate3d },
];

export function ToolRibbon({
  active,
  dragMode,
  dragAllowed,
  dragPending,
  onSelect,
  onDragMode,
}: {
  active: WorkspaceTool;
  dragMode: TcpDragMode;
  dragAllowed: boolean;
  dragPending: boolean;
  onSelect: (tool: WorkspaceTool) => void;
  onDragMode: (mode: TcpDragMode) => void;
}) {
  return (
    <div className="pointer-events-none absolute top-3 left-1/2 z-20 -translate-x-1/2">
      <div className="pointer-events-auto flex items-center gap-1 rounded-xl border border-zinc-950/10 bg-white/90 p-1 shadow-lg ring-1 ring-zinc-950/5 backdrop-blur dark:border-white/10 dark:bg-zinc-800/90 dark:ring-white/10">
        {TOOLS.map((tool, index) => {
          const Icon = tool.icon;
          return (
            <div key={tool.id} className="flex items-center gap-1">
              {index === TOOLS.length - 1 && (
                <span className="mx-0.5 h-5 w-px bg-zinc-950/10 dark:bg-white/10" />
              )}
              <button
                type="button"
                title={`${tool.label} — ${tool.hint}`}
                aria-label={tool.label}
                aria-pressed={active === tool.id}
                onClick={() => onSelect(tool.id)}
                className={`flex size-8 items-center justify-center rounded-lg transition ${
                  active === tool.id
                    ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                    : "text-zinc-500 hover:bg-zinc-950/5 hover:text-zinc-950 dark:text-zinc-400 dark:hover:bg-white/10 dark:hover:text-white"
                }`}
              >
                <Icon className="size-4" />
              </button>
            </div>
          );
        })}
        <span className="mx-0.5 h-5 w-px bg-zinc-950/10 dark:bg-white/10" />
        {DRAG_MODES.map(({ mode, label, hint, icon: Icon }) => (
          <button
            key={mode}
            type="button"
            disabled={!dragAllowed || dragPending}
            title={dragAllowed ? `${label} — ${hint}` : `${label} — requires live control and an alive driver`}
            aria-label={label}
            aria-pressed={dragMode === mode}
            onClick={() => onDragMode(dragMode === mode ? "off" : mode)}
            className={`flex size-8 items-center justify-center rounded-lg transition disabled:cursor-not-allowed disabled:text-zinc-300 dark:disabled:text-zinc-600 ${
              dragMode === mode
                ? "bg-blue-600 text-white dark:bg-blue-500"
                : "text-zinc-500 hover:bg-zinc-950/5 hover:text-zinc-950 dark:text-zinc-400 dark:hover:bg-white/10 dark:hover:text-white"
            }`}
          >
            <Icon className={`size-4 ${dragPending && dragMode === mode ? "animate-pulse" : ""}`} />
          </button>
        ))}
      </div>
    </div>
  );
}
