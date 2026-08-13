import type { SceneGroupKind, SceneItemKind } from "./types";

export function sceneItemVisibilityId(
  kind: SceneItemKind,
  name: string,
): string {
  return kind === "world" ? "world" : `${kind}:${name}`;
}

export function sceneGroupVisibilityId(group: SceneGroupKind): string {
  return `group:${group}`;
}

export function groupForItem(
  kind: Exclude<SceneItemKind, "world">,
): SceneGroupKind {
  if (kind === "device") return "devices";
  if (kind === "frame") return "frames";
  if (kind === "tcp") return "tcps";
  if (kind === "pose") return "poses";
  return "objects";
}

export function isSceneItemHidden(
  hidden: ReadonlySet<string>,
  kind: Exclude<SceneItemKind, "world">,
  name: string,
): boolean {
  return (
    hidden.has("world") ||
    hidden.has(sceneGroupVisibilityId(groupForItem(kind))) ||
    hidden.has(sceneItemVisibilityId(kind, name))
  );
}
