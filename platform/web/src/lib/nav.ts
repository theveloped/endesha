// Page ids in spec §2 rail order. Only overview and io are real pages this
// phase; the rest render disabled in the nav rail (no routes behind them).
export type PageId =
  | "overview"
  | "operate"
  | "programs"
  | "io"
  | "cameras"
  | "vision"
  | "frames"
  | "calibration"
  | "recordings"
  | "flows"
  | "tasks"
  | "system";

export interface NavItem {
  id: PageId;
  label: string;
  glyph: string;
  enabled: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { id: "overview", label: "Overview", glyph: "⌂", enabled: true },
  { id: "operate", label: "Operate", glyph: "✛", enabled: true },
  { id: "programs", label: "Editor", glyph: "≡", enabled: true },
  { id: "io", label: "IO", glyph: "⇄", enabled: true },
  { id: "cameras", label: "Cameras", glyph: "▣", enabled: true },
  { id: "vision", label: "Vision", glyph: "◎", enabled: false },
  { id: "frames", label: "Frames", glyph: "⊿", enabled: true },
  { id: "calibration", label: "Calibration", glyph: "⌖", enabled: false },
  { id: "recordings", label: "Recordings", glyph: "⏺", enabled: false },
  { id: "flows", label: "Flows", glyph: "▦", enabled: true },
  { id: "tasks", label: "Tasks", glyph: "⚑", enabled: true },
  { id: "system", label: "System", glyph: "⚙", enabled: false },
];
