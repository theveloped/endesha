// The state-machine graph of a program (CatalogEntry.graph, exported by
// wf.program.graph from the Python class) rendered with React Flow.
//
// Design view: states, transitions (event / guards), triggers as annotated
// edges, click a node/edge -> the caller jumps to the source line.
// Live overlay (when a ProgramState is given): active states, running actions,
// the transitions that could fire now (waiting_for), the last taken
// transition, and the PackML unit state as the frame colour.
//
// Layout: dagre auto-layout; the user may drag nodes and the positions are
// persisted per program in the config store (config/programs/<name>/layout).
// Unplaced states get auto positions. Nested (compound/parallel) charts render
// flat with a parent badge; swap dagre for elk in `layoutGraph` if we ever
// need real nesting.
import dagre from "@dagrejs/dagre";
import {
  Background,
  BaseEdge,
  Controls,
  EdgeLabelRenderer,
  getBezierPath,
  Handle,
  MarkerType,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Edge,
  type EdgeProps,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { ProgramGraph as GraphData, ProgramState, TransitionEvent, WaitingFor } from "../lib/messages";

// ── data ─────────────────────────────────────────────────────────────────────

export interface GraphLayout {
  positions: Record<string, [number, number]>;
}

export interface LiveOverlay {
  state: ProgramState | null;
  transitions?: TransitionEvent[]; // recent, newest last
}

type StateNodeData = {
  label: string;
  initial: boolean;
  final: boolean;
  parent: string | null;
  kind: string;
  active: boolean;
  running: boolean;
  compact: boolean;
  triggers: { kind: string; label: string }[]; // triggers scoped to this state (timers)
  hasAction: boolean;
  rankdir: "LR" | "TB";
};

type TransEdgeData = {
  event: string | null;
  cond: string[];
  unless: string[];
  trigger: { kind: string; label: string } | null;
  live: "armed" | "taken" | "none";
  compact: boolean;
  onSend?: (event: string) => void;
};

type StateNode = Node<StateNodeData, "state">;
type TransEdge = Edge<TransEdgeData, "trans">;

const NODE_W = 150;
const NODE_H = 46;
const NODE_W_COMPACT = 110;
const NODE_H_COMPACT = 34;

function layoutGraph(graph: GraphData, layout: GraphLayout | null, compact: boolean, rankdir: "LR" | "TB"): Record<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir, nodesep: compact ? 24 : 36, ranksep: compact ? (rankdir === "TB" ? 36 : 70) : (rankdir === "TB" ? 44 : 80), marginx: 10, marginy: 10 });
  g.setDefaultEdgeLabel(() => ({}));
  const w = compact ? NODE_W_COMPACT : NODE_W;
  const h = compact ? NODE_H_COMPACT : NODE_H;
  for (const s of graph.states) g.setNode(s.id, { width: w, height: h });
  for (const t of graph.transitions) if (t.source !== t.target) g.setEdge(t.source, t.target);
  dagre.layout(g);
  const out: Record<string, { x: number; y: number }> = {};
  for (const s of graph.states) {
    const saved = layout?.positions[s.id];
    if (saved) {
      out[s.id] = { x: saved[0], y: saved[1] };
    } else {
      const n = g.node(s.id);
      out[s.id] = { x: n.x - w / 2, y: n.y - h / 2 };
    }
  }
  return out;
}

function triggerLabel(t: { kind: string; params: Record<string, unknown> }): string {
  if (t.kind === "channel") return `${String(t.params.role)}.${String(t.params.channel)} ${String(t.params.edge)}`;
  if (t.kind === "timer") return `after ${String(t.params.seconds)}s`;
  return t.kind;
}

// ── custom node / edge ───────────────────────────────────────────────────────

function StateNodeView({ data, selected }: NodeProps<StateNode>) {
  return (
    <div
      className={cn(
        "relative rounded-lg border-2 bg-white px-3 py-1.5 font-mono shadow-sm dark:bg-zinc-900",
        data.compact ? "text-[11px]" : "text-xs",
        data.final ? "border-double border-4" : "",
        data.active
          ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/40"
          : "border-zinc-300 dark:border-zinc-600",
        selected && "ring-2 ring-sky-400",
      )}
      style={{ width: data.compact ? NODE_W_COMPACT : NODE_W, minHeight: data.compact ? NODE_H_COMPACT : NODE_H }}
      title={[
        data.kind !== "atomic" ? data.kind : null,
        data.parent ? `in ${data.parent}` : null,
        data.hasAction ? "has run_ action" : "no action (passive state)",
      ]
        .filter(Boolean)
        .join(" · ")}
    >
      <Handle type="target" position={data.rankdir === "TB" ? Position.Top : Position.Left} className="!size-1.5 !bg-zinc-400" />
      <Handle type="source" position={data.rankdir === "TB" ? Position.Bottom : Position.Right} className="!size-1.5 !bg-zinc-400" />
      <div className="flex items-center gap-1">
        {data.initial && <span className="size-2 rounded-full bg-zinc-900 dark:bg-white" title="initial" />}
        <span className="truncate font-semibold">{data.label}</span>
        {data.running && (
          <span className="ml-auto inline-block size-2 animate-pulse rounded-full bg-emerald-500" title="action running" />
        )}
      </div>
      {!data.compact && (
        <div className="mt-0.5 flex flex-wrap gap-1 text-[10px] text-zinc-500 dark:text-zinc-400">
          {data.hasAction && <span>run_{data.label}</span>}
          {data.parent && <span>⊂ {data.parent}</span>}
          {data.triggers.map((t, i) => (
            <span key={i} className="rounded bg-sky-500/15 px-1 text-sky-700 dark:text-sky-300">
              {t.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function TransEdgeView({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data, selected, markerEnd }: EdgeProps<TransEdge>) {
  const [path, labelX, labelY] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });
  const live = data?.live ?? "none";
  const stroke = live === "taken" ? "#10b981" : live === "armed" ? "#0ea5e9" : selected ? "#38bdf8" : "#a1a1aa";
  const guards = [...(data?.cond ?? []).map((c) => c), ...(data?.unless ?? []).map((u) => `!${u}`)];
  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={markerEnd}
        style={{ stroke, strokeWidth: live !== "none" ? 2.5 : 1.5, strokeDasharray: live === "armed" ? "6 4" : undefined }}
        className={live === "armed" ? "animate-pulse" : undefined}
      />
      <EdgeLabelRenderer>
        <div
          className={cn(
            "pointer-events-auto absolute flex flex-col items-center rounded border bg-white/95 px-1 py-0.5 font-mono leading-tight shadow-sm dark:bg-zinc-900/95",
            data?.compact ? "text-[9px]" : "text-[10px]",
            live === "taken" && "border-emerald-500",
            live === "armed" && "border-sky-500",
            live === "none" && "border-zinc-200 dark:border-zinc-700",
          )}
          style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
        >
          <span className="flex items-center gap-1">
            <span className="font-semibold">{data?.event ?? "—"}</span>
            {data?.trigger && (
              <span className="rounded bg-sky-500/15 px-1 text-sky-700 dark:text-sky-300" title={`trigger: ${data.trigger.kind}`}>
                {data.trigger.label}
              </span>
            )}
          </span>
          {guards.length > 0 && !data?.compact && <span className="text-zinc-500 dark:text-zinc-400">[{guards.join(" && ")}]</span>}
          {live === "armed" && data?.onSend && data.event && !data.compact && data.trigger === null && (
            <button
              type="button"
              className="cmd mt-0.5 rounded bg-sky-600 px-1 text-white hover:bg-sky-500"
              onClick={(ev) => {
                ev.stopPropagation();
                data.onSend?.(data.event!);
              }}
              title={`Send event ${data.event}`}
            >
              send
            </button>
          )}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

const NODE_TYPES = { state: StateNodeView };
const EDGE_TYPES = { trans: TransEdgeView };

// ── the graph ────────────────────────────────────────────────────────────────

export interface ProgramGraphProps {
  graph: GraphData;
  live?: LiveOverlay;
  layout?: GraphLayout | null;
  compact?: boolean;
  /** Persist dragged positions (omit = not draggable). */
  onLayoutChange?: (layout: GraphLayout) => void;
  onSelectState?: (stateId: string) => void;
  onSelectTransition?: (event: string | null, source: string, target: string) => void;
  onSendEvent?: (event: string) => void;
  className?: string;
}

function ProgramGraphInner({ graph, live, layout = null, compact = false, onLayoutChange, onSelectState, onSelectTransition, onSendEvent, className }: ProgramGraphProps) {
  const { fitView } = useReactFlow();
  // Rank direction follows the container's aspect: wide -> left-to-right,
  // tall/narrow (the right pane) -> top-to-bottom.
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [rankdir, setRankdir] = useState<"LR" | "TB">("LR");
  useEffect(() => {
    const el = hostRef.current;
    if (el === null) return;
    const ro = new ResizeObserver((entries) => {
      const r = entries[0]?.contentRect;
      if (r === undefined || r.width === 0 || r.height === 0) return;
      setRankdir(r.width / r.height >= 1.5 ? "LR" : "TB");
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const graphKey = useMemo(() => JSON.stringify([graph.states.map((s) => s.id), graph.transitions.map((t) => t.id), rankdir]), [graph, rankdir]);
  const positions = useMemo(() => layoutGraph(graph, layout, compact, rankdir), [graph, layout, compact, rankdir]);

  const state = live?.state ?? null;
  const activeStates = useMemo(() => new Set(state?.program_states ?? []), [state]);
  const runningStates = useMemo(() => new Set(state?.actions ?? []), [state]);
  const armed = useMemo(() => {
    const out = new Set<string>();
    if (state === null || state.unit !== "execute") return out;
    for (const w of state.waiting_for ?? []) out.add(w.event);
    return out;
  }, [state]);
  const armedByKind = useMemo(() => {
    const m = new Map<string, WaitingFor>();
    for (const w of state?.waiting_for ?? []) if (!m.has(w.event)) m.set(w.event, w);
    return m;
  }, [state]);
  const lastTaken = useMemo(() => {
    const ts = live?.transitions ?? [];
    for (let i = ts.length - 1; i >= 0; i--) {
      const t = ts[i];
      if (t.scope === "program" && t.source !== null) return t;
    }
    return null;
  }, [live?.transitions]);

  const triggerByEvent = useMemo(() => {
    const m = new Map<string, { kind: string; label: string; state: string | null }>();
    for (const t of graph.triggers ?? []) {
      m.set(t.event, { kind: t.kind, label: triggerLabel(t), state: t.kind === "timer" ? String(t.params.state ?? "") : null });
    }
    return m;
  }, [graph.triggers]);
  const actionStates = useMemo(() => new Set(Object.keys(graph.source?.actions ?? {})), [graph.source]);

  const initialNodes = useMemo<StateNode[]>(
    () =>
      graph.states.map((s) => ({
        id: s.id,
        type: "state",
        position: positions[s.id],
        draggable: onLayoutChange !== undefined,
        data: {
          label: s.id,
          initial: s.initial,
          final: s.final,
          parent: s.parent,
          kind: s.kind,
          active: activeStates.has(s.id),
          running: runningStates.has(s.id),
          compact,
          rankdir,
          hasAction: actionStates.has(s.id),
          triggers: [...triggerByEvent.values()].filter((t) => t.state === s.id).map((t) => ({ kind: t.kind, label: t.label })),
        },
      })),
    [graph.states, positions, activeStates, runningStates, compact, actionStates, triggerByEvent, onLayoutChange, rankdir],
  );

  const initialEdges = useMemo<TransEdge[]>(
    () =>
      graph.transitions.map((t) => {
        const trig = t.event ? triggerByEvent.get(t.event) : undefined;
        let liveKind: TransEdgeData["live"] = "none";
        if (lastTaken && lastTaken.source === t.source && lastTaken.target === t.target && (lastTaken.event ?? null) === (t.event ?? null)) {
          liveKind = "taken";
        } else if (t.event && armed.has(t.event) && activeStates.has(t.source)) {
          const w = armedByKind.get(t.event);
          if (w === undefined || w.target === undefined || w.target === t.target) liveKind = "armed";
        }
        return {
          id: t.id,
          type: "trans",
          source: t.source,
          target: t.target,
          markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: liveKind === "taken" ? "#10b981" : liveKind === "armed" ? "#0ea5e9" : "#a1a1aa" },
          data: {
            event: t.event,
            cond: t.cond,
            unless: t.unless,
            trigger: trig ? { kind: trig.kind, label: trig.label } : null,
            live: liveKind,
            compact,
            onSend: onSendEvent,
          },
        };
      }),
    [graph.transitions, triggerByEvent, lastTaken, armed, armedByKind, activeStates, compact, onSendEvent],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState<StateNode>(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<TransEdge>(initialEdges);
  // Sync derived data (live overlay, layout) into the flow state; keep the
  // user's in-progress drag positions.
  const dragging = useRef(false);
  useEffect(() => {
    if (dragging.current) return;
    setNodes((current) => {
      const byId = new Map(current.map((n) => [n.id, n]));
      return initialNodes.map((n) => {
        const prev = byId.get(n.id);
        return prev && layout?.positions[n.id] === undefined && prev.position ? { ...n, position: prev.position } : n;
      });
    });
  }, [initialNodes, setNodes, layout]);
  useEffect(() => {
    setEdges(initialEdges);
  }, [initialEdges, setEdges]);
  const lastKey = useRef<string | null>(null);
  useEffect(() => {
    if (lastKey.current === graphKey) return;
    lastKey.current = graphKey;
    setNodes(initialNodes);
    const t = setTimeout(() => void fitView({ padding: 0.15, duration: 200 }), 30);
    return () => clearTimeout(t);
  }, [graphKey, initialNodes, setNodes, fitView]);

  const persist = useCallback(
    (moved: StateNode[]) => {
      if (onLayoutChange === undefined) return;
      const positions: Record<string, [number, number]> = { ...(layout?.positions ?? {}) };
      for (const n of moved) positions[n.id] = [Math.round(n.position.x), Math.round(n.position.y)];
      onLayoutChange({ positions });
    },
    [layout, onLayoutChange],
  );

  const [showHelp, setShowHelp] = useState(false);
  return (
    <div ref={hostRef} className={cn("relative h-full w-full", className)}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeDragStart={() => {
          dragging.current = true;
        }}
        onNodeDragStop={(_ev, _node, moved) => {
          dragging.current = false;
          persist(moved as StateNode[]);
        }}
        onNodeClick={(_ev, node) => onSelectState?.(node.id)}
        onEdgeClick={(_ev, edge) => onSelectTransition?.(edge.data?.event ?? null, edge.source, edge.target)}
        nodesConnectable={false}
        elementsSelectable
        fitView
        fitViewOptions={{ padding: 0.15 }}
        minZoom={0.2}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        className="bg-zinc-50 dark:bg-zinc-950"
      >
        <Background gap={16} size={1} color="#d4d4d8" />
        {!compact && <Controls showInteractive={false} position="bottom-right" />}
      </ReactFlow>
      {!compact && (
        <button
          type="button"
          className="absolute left-2 top-2 rounded border border-zinc-300 bg-white/90 px-1.5 text-[10px] text-zinc-500 hover:text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900/90 dark:text-zinc-400"
          onClick={() => setShowHelp((v) => !v)}
        >
          {showHelp ? "hide legend" : "legend"}
        </button>
      )}
      {showHelp && (
        <div className="absolute left-2 top-8 rounded border border-zinc-300 bg-white/95 p-2 text-[10px] leading-relaxed text-zinc-600 shadow dark:border-zinc-700 dark:bg-zinc-900/95 dark:text-zinc-300">
          <div><span className="inline-block size-2 rounded-full bg-zinc-900 dark:bg-white" /> initial · double border = final</div>
          <div><span className="text-emerald-600">green</span> node = active state · pulsing dot = action running</div>
          <div><span className="text-sky-600">dashed blue</span> edge = could fire now (waiting_for)</div>
          <div><span className="text-emerald-600">green</span> edge = last transition taken</div>
          <div>[guard] · blue tag = trigger (channel edge / timer)</div>
          <div>drag nodes to arrange (saved per program); click a node to jump to its code</div>
        </div>
      )}
    </div>
  );
}

export function ProgramGraph(props: ProgramGraphProps) {
  return (
    <ReactFlowProvider>
      <ProgramGraphInner {...props} />
    </ReactFlowProvider>
  );
}
