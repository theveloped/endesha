// Custom React Flow node for the wf editor: a compact card showing the node
// type + id, with a target handle (top) and source handle (bottom). It glows
// with the realm tint while `data.active` (the live task-state node id matches)
// so the operator watches execution walk the graph.
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { cn } from "@/lib/utils";
import type { WfNodeData } from "../../lib/graph";

export default function WfNode({ id, data, selected }: NodeProps) {
  const d = data as WfNodeData;
  const isStart = d.nodeType === "start";
  const isEnd = d.nodeType === "end";
  return (
    <div
      className={cn(
        "min-w-32 rounded border bg-card px-2.5 py-1.5 shadow-sm transition-colors",
        selected ? "border-primary" : "border-border",
        d.active && "border-primary ring-2 ring-primary",
      )}
    >
      {!isStart && (
        <Handle type="target" position={Position.Top} className="!bg-muted-foreground" />
      )}
      <div className="font-mono text-xs font-medium text-foreground">
        {d.nodeType}
      </div>
      <div className="font-mono text-[10px] text-muted-foreground">{id}</div>
      {!isEnd && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!bg-muted-foreground"
        />
      )}
    </div>
  );
}
