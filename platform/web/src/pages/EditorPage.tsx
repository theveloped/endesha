// Node editor (design: node-graph authoring — the "n8n/Blender for robotics"
// surface). A React Flow canvas where operators compose skill/flow graphs from
// typed nodes, wire exec edges, edit per-node params, Save (flows/cmd/save),
// bring online + Run, and watch the live active node highlight from the task
// state. Graph docs are role-bound repo files served by the supervisor
// (flows/doc + flows/cmd/save); running reuses flows/cmd/start + task/cmd/start.
import "@xyflow/react/dist/style.css";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  addEdge,
  useEdgesState,
  useNodesState,
  type Connection,
} from "@xyflow/react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import WfNode from "../components/nodegraph/WfNode";
import { query, subscribeLatest, watchAlive, type Unsubscribe } from "../lib/bus";
import {
  fetchFlowDoc,
  saveFlowDoc,
  startFlow,
  startTask,
} from "../lib/actions";
import { flowsCatalog, supervisorAlive, taskState } from "../lib/config";
import {
  PALETTE,
  docToFlow,
  flowToDoc,
  newNodeId,
  type WfEdge,
  type WfNode as WfNodeT,
  type WfNodeData,
} from "../lib/graph";
import type {
  FlowCatalogEntry,
  FlowsCatalog,
  GraphDoc,
} from "../lib/messages";

const nodeTypes = { wf: WfNode };

interface EditorPageProps {
  session: Session | null;
  realm: string;
  wsConnected: boolean;
  commandsEnabled: boolean;
}

export default function EditorPage(props: EditorPageProps) {
  return (
    <ReactFlowProvider>
      <Editor {...props} />
    </ReactFlowProvider>
  );
}

function Editor({ session, realm, wsConnected, commandsEnabled }: EditorPageProps) {
  const [flows, setFlows] = useState<FlowCatalogEntry[]>([]);
  const [supUp, setSupUp] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [meta, setMeta] = useState<{
    name: string;
    kind: "flow" | "skill";
    roles?: GraphDoc["roles"];
  } | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState<WfNodeT>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<WfEdge>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [newName, setNewName] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const activeRef = useRef<string | null>(null);

  // ── catalog (graph flows) + supervisor liveness ──────────────────────────
  useEffect(() => {
    setFlows([]);
    setSupUp(false);
    if (session === null) return;
    const unsubs: Unsubscribe[] = [];
    let disposed = false;
    void (async () => {
      const all = await Promise.all([
        subscribeLatest(
          session,
          flowsCatalog(realm),
          (m) => setFlows((m as FlowsCatalog).flows ?? []),
          4,
        ),
        watchAlive(session, supervisorAlive(realm), setSupUp),
      ]);
      if (disposed) {
        for (const u of all) u();
        return;
      }
      unsubs.push(...all);
      const current = await query(session, flowsCatalog(realm), {});
      if (!disposed && current !== null)
        setFlows((current as FlowsCatalog).flows ?? []);
    })();
    return () => {
      disposed = true;
      for (const u of unsubs) u();
    };
  }, [session, realm]);

  const graphFlows = useMemo(
    () => flows.filter((f) => f.kind === "graph"),
    [flows],
  );
  const online = useMemo(
    () => new Set(flows.filter((f) => f.online).map((f) => f.name)),
    [flows],
  );

  // ── load a flow's doc onto the canvas ─────────────────────────────────────
  const loadFlow = useCallback(
    async (name: string) => {
      if (session === null) return;
      setMsg(null);
      setSelectedNode(null);
      try {
        const reply = await fetchFlowDoc(session, realm, name);
        if (!reply.ok || reply.doc === undefined) {
          setMsg(reply.error ?? "load failed");
          return;
        }
        if (reply.kind !== "graph") {
          setMsg(`${name} is a legacy spec flow (not editable here)`);
          setNodes([]);
          setEdges([]);
          setMeta(null);
          setSelected(name);
          return;
        }
        const doc = reply.doc as GraphDoc;
        const { nodes: n, edges: e } = docToFlow(doc);
        setNodes(n);
        setEdges(e);
        setMeta({ name: doc.name, kind: doc.kind ?? "flow", roles: doc.roles });
        setSelected(name);
      } catch (err) {
        setMsg(String(err));
      }
    },
    [session, realm, setNodes, setEdges],
  );

  // ── live active-node highlight from the task state ────────────────────────
  useEffect(() => {
    activeRef.current = null;
    if (session === null || selected === null) return;
    let disposed = false;
    let unsub: Unsubscribe | null = null;
    void (async () => {
      const u = await subscribeLatest(
        session,
        taskState(realm, selected),
        (m) => {
          const active = (m as { active?: string | null }).active ?? null;
          if (active === activeRef.current) return;
          activeRef.current = active;
          setNodes((ns) =>
            ns.map((n) => ({
              ...n,
              data: { ...(n.data as WfNodeData), active: n.id === active },
            })),
          );
        },
        4,
      );
      if (disposed) u();
      else unsub = u;
    })();
    return () => {
      disposed = true;
      if (unsub !== null) unsub();
    };
  }, [session, realm, selected, setNodes]);

  // ── canvas edits ──────────────────────────────────────────────────────────
  const onConnect = useCallback(
    (c: Connection) =>
      setEdges((es) =>
        addEdge(
          { ...c, data: { kind: "exec", port: "out" } } as WfEdge,
          es,
        ),
      ),
    [setEdges],
  );

  const addNode = useCallback(
    (type: string, defaults: Record<string, unknown>) => {
      setNodes((ns) => {
        const id = newNodeId(type, new Set(ns.map((n) => n.id)));
        const next: WfNodeT = {
          id,
          type: "wf",
          position: { x: 260, y: 40 + ns.length * 20 },
          data: { nodeType: type, params: { ...defaults } },
        };
        return [...ns, next];
      });
    },
    [setNodes],
  );

  const createFlow = useCallback(() => {
    const name = newName.trim();
    if (!name) return;
    setNodes([
      {
        id: "start",
        type: "wf",
        position: { x: 120, y: 40 },
        data: { nodeType: "start", params: {} },
      },
    ]);
    setEdges([]);
    setMeta({ name, kind: "flow", roles: { arm: { contract: "arm" } } });
    setSelected(name);
    setSelectedNode(null);
    setNewName("");
    setMsg("new flow — add nodes, then Save");
  }, [newName, setNodes, setEdges]);

  const selectedNodeObj = nodes.find((n) => n.id === selectedNode) ?? null;

  const updateParams = useCallback(
    (raw: string) => {
      if (selectedNode === null) return;
      let parsed: Record<string, unknown>;
      try {
        parsed = JSON.parse(raw);
      } catch {
        setMsg("params: invalid JSON");
        return;
      }
      setMsg(null);
      setNodes((ns) =>
        ns.map((n) =>
          n.id === selectedNode
            ? { ...n, data: { ...(n.data as WfNodeData), params: parsed } }
            : n,
        ),
      );
    },
    [selectedNode, setNodes],
  );

  const deleteSelectedNode = useCallback(() => {
    if (selectedNode === null) return;
    setNodes((ns) => ns.filter((n) => n.id !== selectedNode));
    setEdges((es) =>
      es.filter((e) => e.source !== selectedNode && e.target !== selectedNode),
    );
    setSelectedNode(null);
  }, [selectedNode, setNodes, setEdges]);

  // ── save / run ────────────────────────────────────────────────────────────
  const gated = wsConnected && commandsEnabled && supUp && session !== null;

  const doSave = useCallback(async () => {
    if (session === null || meta === null) return;
    setBusy(true);
    setMsg(null);
    try {
      const doc = flowToDoc(meta, nodes, edges);
      const reply = await saveFlowDoc(session, realm, meta.name, doc);
      setMsg(reply.ok ? `saved ${meta.name}` : (reply.error ?? "save failed"));
    } catch (err) {
      setMsg(String(err));
    } finally {
      setBusy(false);
    }
  }, [session, realm, meta, nodes, edges]);

  const doRun = useCallback(async () => {
    if (session === null || meta === null) return;
    setBusy(true);
    setMsg(null);
    try {
      if (!online.has(meta.name)) {
        const on = await startFlow(session, realm, meta.name);
        if (!on.ok) {
          setMsg(on.error ?? "bring-online failed");
          return;
        }
        // give the task_runner a moment to declare its cmd/start queryable
        await new Promise((r) => setTimeout(r, 600));
      }
      const started = await startTask(session, realm, meta.name);
      setMsg(started.ok ? `running ${meta.name}` : (started.error ?? "run rejected"));
    } catch (err) {
      setMsg(String(err));
    } finally {
      setBusy(false);
    }
  }, [session, realm, meta, online]);

  return (
    <div className="grid h-full min-h-0 grid-cols-[200px_1fr_260px]">
      {/* left: flow list + new */}
      <div className="flex min-h-0 flex-col gap-2 overflow-y-auto border-r border-border p-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium">Flows</span>
          <Badge
            variant="outline"
            className={
              supUp
                ? "border-ok bg-ok/20 text-ok"
                : "border-destructive bg-destructive/20 text-destructive"
            }
          >
            {supUp ? "sup up" : "sup down"}
          </Badge>
        </div>
        {graphFlows.length === 0 && (
          <p className="text-xs text-muted-foreground">no graph flows yet</p>
        )}
        {graphFlows.map((f) => (
          <button
            key={f.name}
            onClick={() => void loadFlow(f.name)}
            className={cnBtn(f.name === selected)}
          >
            <span className="font-mono text-xs">{f.name}</span>
            {f.online && (
              <span className="ml-1 text-[10px] text-ok">● online</span>
            )}
          </button>
        ))}
        <div className="mt-2 flex flex-col gap-1 border-t border-border pt-2">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="new flow name"
            className="rounded border border-input bg-background px-1.5 py-1 font-mono text-xs"
          />
          <Button size="sm" variant="outline" onClick={createFlow} disabled={!newName.trim()}>
            New graph
          </Button>
        </div>
      </div>

      {/* center: canvas + toolbar */}
      <div className="relative min-h-0">
        {meta === null ? (
          <div className="flex h-full items-center justify-center p-8 text-center text-sm text-muted-foreground">
            select a graph flow on the left, or create a new one
          </div>
        ) : (
          <>
            <div className="absolute left-2 top-2 z-10 flex items-center gap-1 rounded border border-border bg-card/90 p-1">
              <span className="px-1 font-mono text-xs">{meta.name}</span>
              {PALETTE.map((p) => (
                <Button
                  key={p.type}
                  size="sm"
                  variant="outline"
                  className="h-6 px-1.5 text-[11px]"
                  onClick={() => addNode(p.type, p.defaults)}
                  title={`add ${p.type}`}
                >
                  +{p.label}
                </Button>
              ))}
            </div>
            <div className="absolute right-2 top-2 z-10 flex items-center gap-1">
              <Button
                size="sm"
                className="cmd"
                variant="outline"
                onClick={() => void doSave()}
                disabled={!gated || busy}
              >
                Save
              </Button>
              <Button
                size="sm"
                className="cmd"
                onClick={() => void doRun()}
                disabled={!gated || busy}
                title="bring online + task/cmd/start"
              >
                Run
              </Button>
            </div>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={(_, n) => setSelectedNode(n.id)}
              onPaneClick={() => setSelectedNode(null)}
              nodeTypes={nodeTypes}
              fitView
              proOptions={{ hideAttribution: true }}
            >
              <Background />
              <Controls />
              <MiniMap pannable zoomable />
            </ReactFlow>
          </>
        )}
      </div>

      {/* right: param panel */}
      <div className="min-h-0 space-y-2 overflow-y-auto border-l border-border p-2">
        <span className="text-sm font-medium">Inspector</span>
        {msg !== null && (
          <p className="rounded bg-muted px-1.5 py-1 text-xs text-muted-foreground">
            {msg}
          </p>
        )}
        {selectedNodeObj === null ? (
          <p className="text-xs text-muted-foreground">
            select a node to edit its params
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            <div>
              <div className="text-[10px] uppercase text-muted-foreground">id</div>
              <div className="font-mono text-xs">{selectedNodeObj.id}</div>
            </div>
            <div>
              <div className="text-[10px] uppercase text-muted-foreground">type</div>
              <div className="font-mono text-xs">
                {(selectedNodeObj.data as WfNodeData).nodeType}
              </div>
            </div>
            <div>
              <div className="text-[10px] uppercase text-muted-foreground">
                params (JSON)
              </div>
              <ParamsEditor
                key={selectedNodeObj.id}
                value={(selectedNodeObj.data as WfNodeData).params}
                onApply={updateParams}
              />
            </div>
            <Button size="sm" variant="outline" onClick={deleteSelectedNode}>
              Delete node
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

function ParamsEditor({
  value,
  onApply,
}: {
  value: Record<string, unknown>;
  onApply: (raw: string) => void;
}) {
  const [text, setText] = useState(() => JSON.stringify(value, null, 2));
  return (
    <div className="flex flex-col gap-1">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        spellCheck={false}
        rows={8}
        className="w-full rounded border border-input bg-background p-1.5 font-mono text-[11px]"
      />
      <Button size="sm" variant="outline" onClick={() => onApply(text)}>
        Apply
      </Button>
    </div>
  );
}

function cnBtn(active: boolean): string {
  return [
    "rounded border px-1.5 py-1 text-left",
    active
      ? "border-primary bg-primary/10"
      : "border-border hover:bg-accent",
  ].join(" ");
}
