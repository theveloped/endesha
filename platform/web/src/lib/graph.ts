// Node-graph <-> React Flow conversion + the editor's node-type palette.
// Mirrors wf/services/task_runner/{graph.py,nodes.py}: exec edges carry a
// `port` (default "out"; branch emits "true"/"false"), data edges pass an
// upstream output (from `node.key`) into a downstream input (`node.key`).
//
// Node positions aren't part of the runtime model, so we stash an extra
// `position` key on each doc node: graph.py's validator ignores unknown node
// keys, but the supervisor writes the doc verbatim, so layout round-trips.
import type { Edge, Node } from "@xyflow/react";
import type { GraphDoc, GraphEdgeDoc, GraphNodeDoc } from "./messages";

export interface PaletteEntry {
  type: string;
  label: string;
  /** default params seeded when the node is added. */
  defaults: Record<string, unknown>;
}

// The v1 vocabulary (task_runner nodes.py NODE_TYPES), with author-friendly
// defaults for the param panel.
export const PALETTE: PaletteEntry[] = [
  { type: "start", label: "Start", defaults: {} },
  { type: "end", label: "End", defaults: {} },
  { type: "move", label: "Move", defaults: { motion: "movej", pose_name: "" } },
  { type: "grip", label: "Grip", defaults: { action: "close" } },
  { type: "set_do", label: "Set DO", defaults: { bank: "standard", pin: 0, value: true } },
  { type: "wait_di", label: "Wait DI", defaults: { pin: 0, timeout_s: 5.0, level: true } },
  { type: "vision.start", label: "Vision start", defaults: { format: "Any" } },
  { type: "vision.stop", label: "Vision stop", defaults: {} },
  { type: "detect", label: "Detect", defaults: {} },
  { type: "branch", label: "Branch (if)", defaults: { input: "" } },
];

export interface WfNodeData {
  nodeType: string;
  params: Record<string, unknown>;
  active?: boolean;
  [key: string]: unknown;
}

export type WfNode = Node<WfNodeData>;
export interface WfEdgeData {
  kind: "exec" | "data";
  port: string;
  fromKey?: string | null;
  toKey?: string | null;
  [key: string]: unknown;
}
export type WfEdge = Edge<WfEdgeData>;

function endpoint(node: string, key?: string | null): string {
  return key ? `${node}.${key}` : node;
}

/** Convert an authored doc into React Flow nodes + edges. */
export function docToFlow(doc: GraphDoc): { nodes: WfNode[]; edges: WfEdge[] } {
  const nodes: WfNode[] = doc.nodes.map((n, i) => {
    const pos = (n as GraphNodeDoc & { position?: { x: number; y: number } })
      .position;
    return {
      id: n.id,
      type: "wf",
      position: pos ?? { x: 40, y: 40 + i * 90 },
      data: { nodeType: n.type, params: { ...(n.params ?? {}) } },
    };
  });
  const edges: WfEdge[] = (doc.edges ?? []).map((e, i) => {
    const [src, srcKey] = e.from.split(".");
    const [dst, dstKey] = e.to.split(".");
    const kind = e.kind ?? "exec";
    const port = e.port ?? "out";
    return {
      id: `e${i}-${src}-${dst}`,
      source: src,
      target: dst,
      animated: kind === "data",
      label: kind === "data" ? "data" : port !== "out" ? port : undefined,
      data: { kind, port, fromKey: srcKey ?? null, toKey: dstKey ?? null },
    };
  });
  return { nodes, edges };
}

/** Convert the canvas back into a savable doc (positions preserved). */
export function flowToDoc(
  meta: { name: string; kind: "flow" | "skill"; roles?: GraphDoc["roles"] },
  nodes: WfNode[],
  edges: WfEdge[],
): GraphDoc {
  const docNodes: (GraphNodeDoc & { position: { x: number; y: number } })[] =
    nodes.map((n) => ({
      id: n.id,
      type: n.data.nodeType,
      params: n.data.params,
      position: { x: Math.round(n.position.x), y: Math.round(n.position.y) },
    }));
  const docEdges: GraphEdgeDoc[] = edges.map((e) => {
    const d = e.data ?? { kind: "exec", port: "out" };
    const edge: GraphEdgeDoc = {
      from: endpoint(e.source, d.fromKey),
      to: endpoint(e.target, d.toKey),
    };
    if (d.kind === "data") edge.kind = "data";
    if (d.kind !== "data" && d.port && d.port !== "out") edge.port = d.port;
    return edge;
  });
  return {
    name: meta.name,
    kind: meta.kind,
    ...(meta.roles ? { roles: meta.roles } : {}),
    nodes: docNodes,
    edges: docEdges,
  };
}

let _seq = 0;
/** A unique node id for a freshly added palette node. */
export function newNodeId(type: string, existing: Set<string>): string {
  const base = type.replace(/[^a-z0-9]+/gi, "_").toLowerCase();
  let id = base;
  while (existing.has(id)) id = `${base}_${++_seq}`;
  return id;
}
