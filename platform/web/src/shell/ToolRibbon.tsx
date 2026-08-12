import {
  Activity,
  Camera,
  Hand,
  Move3d,
  RadioTower,
  Settings2,
  SlidersHorizontal,
} from "lucide-react";

export type WorkspaceTool =
  | "overview"
  | "operate"
  | "io"
  | "cameras"
  | "configuration"
  | "topics";

const TOOLS: Array<{
  id: WorkspaceTool;
  label: string;
  hint: string;
  icon: typeof Activity;
}> = [
  { id: "overview", label: "Overview", hint: "Cell status and engineering motion", icon: Activity },
  { id: "operate", label: "Operate", hint: "Joint and Cartesian jogging", icon: Hand },
  { id: "io", label: "IO", hint: "Digital and analog signals", icon: SlidersHorizontal },
  { id: "cameras", label: "Cameras", hint: "Images and acquisition", icon: Camera },
  { id: "topics", label: "Topics", hint: "Raw Zenoh samples and metadata", icon: RadioTower },
  { id: "configuration", label: "Configure", hint: "Frames, TCPs, poses and device sources", icon: Settings2 },
];

export const TOOL_META = TOOLS;

export function ToolRibbon({
  active,
  dragActive,
  dragAllowed,
  dragPending,
  onSelect,
  onToggleDrag,
}: {
  active: WorkspaceTool;
  dragActive: boolean;
  dragAllowed: boolean;
  dragPending: boolean;
  onSelect: (tool: WorkspaceTool) => void;
  onToggleDrag: () => void;
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
        <button
          type="button"
          disabled={!dragAllowed || dragPending}
          title={
            dragAllowed
              ? dragActive
                ? "Disable TCP drag handles"
                : "Drag active TCP — enable interactive Cartesian positioning"
              : "TCP drag requires live control and an alive driver"
          }
          aria-label="Drag active TCP"
          aria-pressed={dragActive}
          onClick={onToggleDrag}
          className={`flex size-8 items-center justify-center rounded-lg transition disabled:cursor-not-allowed disabled:text-zinc-300 dark:disabled:text-zinc-600 ${
            dragActive
              ? "bg-blue-600 text-white dark:bg-blue-500"
              : "text-zinc-500 hover:bg-zinc-950/5 hover:text-zinc-950 dark:text-zinc-400 dark:hover:bg-white/10 dark:hover:text-white"
          }`}
        >
          <Move3d className={`size-4 ${dragPending ? "animate-pulse" : ""}`} />
        </button>
      </div>
    </div>
  );
}
