export type UIMode = "observe" | "teach" | "build" | "program" | "debug";

export type RailSection =
  | "scene"
  | "add"
  | "programs"
  | "cameras"
  | "frames"
  | "io"
  | "recordings"
  | "settings";

export type RightWorkspace =
  | { type: "closed" }
  | { type: "scene" }
  | { type: "programs" }
  | { type: "camera"; cameraId: string }
  | { type: "frame"; frameId: string }
  | { type: "io" }
  | { type: "recordings" }
  | { type: "settings" };

export type FrameCreationMethod = "tcp" | "manual";

export type ActiveTool =
  | { type: "none" }
  | { type: "jog"; armId: string }
  | { type: "add-frame"; method: FrameCreationMethod };

export type Selection =
  | { kind: "robot"; id: string; label: string }
  | { kind: "camera"; id: string; label: string }
  | { kind: "frame"; id: string; label: string }
  | { kind: "scene"; id: string; label: string }
  | { kind: "io"; id: string; label: string }
  | { kind: "program"; id: string; label: string };

export interface CommandCapabilities {
  inspect: boolean;
  configure: boolean;
  ioWrite: boolean;
  motion: boolean;
  jog: boolean;
  reason: string | null;
}

export function workspaceTitle(workspace: RightWorkspace): string {
  switch (workspace.type) {
    case "scene":
      return "Cell inspection";
    case "programs":
      return "Programs and flows";
    case "camera":
      return `Camera ${workspace.cameraId}`;
    case "frame":
      return `Frame ${workspace.frameId}`;
    case "io":
      return "Cell IO";
    case "recordings":
      return "Replay and recordings";
    case "settings":
      return "Interface settings";
    case "closed":
      return "Closed";
  }
}
