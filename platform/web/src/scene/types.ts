import type { TcpDef } from "../lib/messages";

export type ScenePreview =
  | { kind: "pose"; name: string; q: number[] }
  | { kind: "tcp"; name: string; def: TcpDef }
  | null;
