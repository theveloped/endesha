// Minimal hash router (no dependency): the URL is the source of truth for the
// realm and the active tool, so views are deep-linkable and the back button
// works.
//
//   #/cell/<tool>            the engineering workspace of the active cell
//   #/cell/program/<name?>   full-page program studio (files, graph, editor)
//   #/cell/topics            full-page topic inspector for the active cell
//   #/cell/hmi               the operator page (legacy #/hmi still parses)
//   #/replay/<sid>/<tool>    a recording
//
import { useCallback, useMemo, useSyncExternalStore } from "react";
import type { WorkspaceTool } from "./ToolRibbon";
import { TOOL_META } from "./ToolRibbon";

export type Route =
  | { kind: "cell"; tool: WorkspaceTool }
  | { kind: "program"; name: string | null }
  | { kind: "topics" }
  | { kind: "hmi" }
  | { kind: "replay"; sid: string | null; tool: WorkspaceTool };

const DEFAULT_TOOL: WorkspaceTool = "overview";

function isTool(value: string | undefined): value is WorkspaceTool {
  return value !== undefined && TOOL_META.some((t) => t.id === value);
}

export function parseRoute(hash: string): Route {
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  if (parts[0] === "hmi") return { kind: "hmi" };
  if (parts[0] === "replay") {
    const sid = parts[1] ?? null;
    return { kind: "replay", sid, tool: isTool(parts[2]) ? parts[2] : DEFAULT_TOOL };
  }
  if (parts[0] === "cell" && parts[1] === "hmi") return { kind: "hmi" };
  if (parts[0] === "cell" && parts[1] === "topics") return { kind: "topics" };
  if (parts[0] === "cell" && parts[1] === "program") return { kind: "program", name: parts[2] ?? null };
  return { kind: "cell", tool: isTool(parts[1]) ? parts[1] : DEFAULT_TOOL };
}

export function routeToHash(route: Route): string {
  switch (route.kind) {
    case "hmi":
      return "#/cell/hmi";
    case "topics":
      return "#/cell/topics";
    case "program":
      return route.name === null ? "#/cell/program" : `#/cell/program/${encodeURIComponent(route.name)}`;
    case "replay":
      return route.sid === null
        ? `#/replay`
        : `#/replay/${encodeURIComponent(route.sid)}/${route.tool}`;
    default:
      return `#/cell/${route.tool}`;
  }
}

function subscribe(onChange: () => void) {
  window.addEventListener("hashchange", onChange);
  return () => window.removeEventListener("hashchange", onChange);
}

function snapshot(): string {
  return window.location.hash;
}

export function navigate(route: Route, { replace = false } = {}): void {
  const hash = routeToHash(route);
  if (window.location.hash === hash) return;
  if (replace) window.history.replaceState(null, "", hash);
  else window.location.hash = hash;
  if (replace) window.dispatchEvent(new HashChangeEvent("hashchange"));
}

export function useRoute(): [Route, (route: Route) => void] {
  const hash = useSyncExternalStore(subscribe, snapshot, snapshot);
  // Stable identity per hash: effects keyed on the route must not re-fire on
  // every render.
  const route = useMemo(() => parseRoute(hash), [hash]);
  const go = useCallback((route: Route) => navigate(route), []);
  return [route, go];
}
