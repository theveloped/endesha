import type {
  DeviceEntry,
  FrameDef,
  PoseDef,
  SceneObject,
  TcpDef,
} from "../lib/messages";

export type ScenePreview =
  | { kind: "pose"; name: string; q: number[] }
  | { kind: "tcp"; name: string; def: TcpDef }
  | null;

export type SceneItemKind =
  | "world"
  | "device"
  | "frame"
  | "tcp"
  | "pose"
  | "object";

export type SceneGroupKind =
  | "devices"
  | "frames"
  | "tcps"
  | "poses"
  | "objects";

export type SceneItemSelection =
  | { kind: "world"; name: "world" }
  | { kind: "device"; name: string; value: DeviceEntry }
  | { kind: "frame"; name: string; value: FrameDef }
  | { kind: "tcp"; name: string; value: TcpDef }
  | { kind: "pose"; name: string; value: PoseDef }
  | { kind: "object"; name: string; value: SceneObject };

export type SceneSelection =
  | SceneItemSelection
  | { kind: "group"; name: SceneGroupKind };

export type SceneCreateKind = "frame" | "tcp" | "pose" | "object";

export interface SceneCreateRequest {
  kinds: SceneCreateKind[];
  parent: SceneItemSelection | null;
  initialKind?: SceneCreateKind;
}
