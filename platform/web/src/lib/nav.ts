// Implemented operator pages in rail order.
export type PageId =
  | "overview"
  | "operate"
  | "io"
  | "cameras"
  | "frames"
  | "recordings";

export interface NavItem {
  id: PageId;
  label: string;
  glyph: string;
  enabled: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { id: "overview", label: "Overview", glyph: "⌂", enabled: true },
  { id: "operate", label: "Operate", glyph: "✛", enabled: true },
  { id: "io", label: "IO", glyph: "⇄", enabled: true },
  { id: "cameras", label: "Cameras", glyph: "▣", enabled: true },
  { id: "frames", label: "Frames", glyph: "⊿", enabled: true },
  { id: "recordings", label: "Recordings", glyph: "⏺", enabled: false },
];
