import { Box, Camera, Eye, EyeOff, Focus, Frame } from "lucide-react";
import type { ViewerVisibility } from "../scene/viewerControls";

const LAYERS: Array<{
  id: keyof ViewerVisibility;
  label: string;
  hint: string;
  color: string;
  icon: typeof Frame;
}> = [
  {
    id: "frames",
    label: "Frames",
    hint: "Configured coordinate frames",
    color: "linear-gradient(135deg, #ef4444 0 33%, #22c55e 33% 66%, #3b82f6 66%)",
    icon: Frame,
  },
  {
    id: "tcp",
    label: "Active TCP",
    hint: "Live tool-center-point marker",
    color: "#22d3ee",
    icon: Focus,
  },
  {
    id: "camera",
    label: "Camera",
    hint: "Live camera frustum",
    color: "#f59e0b",
    icon: Camera,
  },
  {
    id: "scene",
    label: "Scene",
    hint: "Configured meshes and tooling",
    color: "#71717a",
    icon: Box,
  },
];

export function ViewportLegend({
  visibility,
  onChange,
}: {
  visibility: ViewerVisibility;
  onChange: (visibility: ViewerVisibility) => void;
}) {
  const toggle = (id: keyof ViewerVisibility) =>
    onChange({ ...visibility, [id]: !visibility[id] });

  return (
    <div className="pointer-events-auto absolute bottom-3 left-3 z-10 w-52 rounded-lg border border-zinc-950/10 bg-white/90 p-2.5 shadow-lg ring-1 ring-zinc-950/5 backdrop-blur dark:border-white/10 dark:bg-zinc-800/90 dark:ring-white/10">
      <div className="mb-1.5 flex items-center justify-between gap-2 text-[10px] font-semibold uppercase tracking-wider text-zinc-500 dark:text-zinc-400">
        <span>Viewer layers</span>
        <span>{LAYERS.filter((layer) => visibility[layer.id]).length}/{LAYERS.length}</span>
      </div>
      <div className="flex flex-col gap-0.5">
        {LAYERS.map((layer) => {
          const visible = visibility[layer.id];
          const Icon = layer.icon;
          const StateIcon = visible ? Eye : EyeOff;
          return (
            <button
              key={layer.id}
              type="button"
              aria-label={`${visible ? "Hide" : "Show"} ${layer.label}`}
              aria-pressed={visible}
              title={`${layer.label} — ${layer.hint}`}
              onClick={() => toggle(layer.id)}
              className={`flex h-7 items-center gap-2 rounded-md px-1.5 text-left text-xs/5 transition ${
                visible
                  ? "text-zinc-950 hover:bg-zinc-950/5 dark:text-white dark:hover:bg-white/10"
                  : "text-zinc-400 hover:bg-zinc-950/5 dark:text-zinc-500 dark:hover:bg-white/10"
              }`}
            >
              <span
                className="size-2.5 shrink-0 rounded-[3px] ring-1 ring-black/10"
                style={{ background: visible ? layer.color : "transparent" }}
              />
              <Icon className="size-3.5 shrink-0" />
              <span className="min-w-0 flex-1 truncate">{layer.label}</span>
              <StateIcon className="size-3.5 shrink-0" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
