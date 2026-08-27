// Layout hooks: a resize-aware window width and remembered pane widths that
// read localStorage once (in the state initializer), not on every render.
import { useCallback, useEffect, useState } from "react";
import type { WorkspaceTool } from "./ToolRibbon";

/** Default right-pane width per tool. */
export const RIGHT_DEFAULT_WIDTH: Record<WorkspaceTool, number> = {
  overview: 360,
  operate: 560,
  programs: 520,
  io: 560,
  cameras: 620,
  configuration: 620,
};

export function useWindowWidth(): number {
  const [width, setWidth] = useState(() => window.innerWidth);
  useEffect(() => {
    const onResize = () => setWidth(window.innerWidth);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return width;
}

export function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

// Read each key from localStorage once per page load; renders hit the cache.
const stored = new Map<string, number | null>();

function readStored(key: string): number | null {
  if (!stored.has(key)) {
    const value = Number(localStorage.getItem(key));
    stored.set(key, Number.isFinite(value) && value > 0 ? value : null);
  }
  return stored.get(key) ?? null;
}

/** A pane width persisted under `key`; `initial` when nothing is stored. The
 *  returned width is clamped to [min, max] so a shrinking window never leaves
 *  a pane wider than the space it has. */
export function useRememberedWidth(
  key: string,
  initial: number,
  min: number,
  max: number,
): [number, (width: number) => void] {
  const [widths, setWidths] = useState<Record<string, number>>({});
  const current = widths[key] ?? readStored(key) ?? initial;
  const width = clamp(current, min, max);
  const update = useCallback(
    (next: number) => {
      const value = clamp(next, min, max);
      setWidths((previous) => ({ ...previous, [key]: value }));
      stored.set(key, value);
      localStorage.setItem(key, String(value));
    },
    [key, min, max],
  );
  return [width, update];
}
