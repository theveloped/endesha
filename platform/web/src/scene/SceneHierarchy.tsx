import { useMemo, useState } from "react";
import {
  Box,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Cpu,
  Focus,
  Frame,
  GitBranch,
  List,
  Radio,
  RefreshCw,
  Waypoints,
} from "lucide-react";
import { Button } from "../catalyst/button";
import type {
  DeviceEntry,
  FrameDef,
  PoseDef,
  SceneObject,
  TcpDef,
} from "../lib/messages";
import type { SceneStructure } from "./useSceneStructure";

export type SceneSelection =
  | { kind: "world"; name: "world" }
  | { kind: "device"; name: string; value: DeviceEntry }
  | { kind: "frame"; name: string; value: FrameDef }
  | { kind: "tcp"; name: string; value: TcpDef }
  | { kind: "pose"; name: string; value: PoseDef }
  | { kind: "object"; name: string; value: SceneObject };

type NodeKind = SceneSelection["kind"];

interface TreeNode {
  id: string;
  label: string;
  secondary?: string;
  kind: NodeKind;
  selection: SceneSelection;
  children: TreeNode[];
}

const ICON_BY_KIND: Record<NodeKind, typeof Box> = {
  world: GitBranch,
  device: Cpu,
  frame: Frame,
  tcp: Focus,
  pose: Waypoints,
  object: Box,
};

function leaf(name: string): string {
  const parts = name.split("/");
  return parts[parts.length - 1] ?? name;
}

function makeTree(structure: SceneStructure): TreeNode {
  const root: TreeNode = {
    id: "world",
    label: "World",
    secondary: "frame",
    kind: "world",
    selection: { kind: "world", name: "world" },
    children: [],
  };
  const byAnchor = new Map<string, TreeNode>([["world", root]]);
  const armNodes = new Map<string, TreeNode>();

  for (const device of structure.devices.filter((item) => item.contract === "arm")) {
    const node: TreeNode = {
      id: `device:${device.id}`,
      label: device.id,
      secondary: device.model ?? device.contract,
      kind: "device",
      selection: { kind: "device", name: device.id, value: device },
      children: [],
    };
    root.children.push(node);
    armNodes.set(device.id, node);
    byAnchor.set(`device:${device.id}`, node);
  }

  const remainingFrames = new Map(
    structure.frames.map((frame) => [frame.name, frame]),
  );
  let progressed = true;
  while (remainingFrames.size > 0 && progressed) {
    progressed = false;
    for (const [name, frame] of remainingFrames) {
      const armMatch = /^arm\/([^/]+)\/base$/.exec(name);
      const parent =
        (armMatch === null ? undefined : armNodes.get(armMatch[1])) ??
        byAnchor.get(frame.def.parent);
      if (parent === undefined) continue;
      const node: TreeNode = {
        id: `frame:${name}`,
        label: leaf(name),
        secondary: "frame",
        kind: "frame",
        selection: { kind: "frame", name, value: frame.def },
        children: [],
      };
      parent.children.push(node);
      byAnchor.set(name, node);
      remainingFrames.delete(name);
      progressed = true;
    }
  }
  for (const [name, frame] of remainingFrames) {
    const node: TreeNode = {
      id: `frame:${name}`,
      label: leaf(name),
      secondary: `frame · ${frame.def.parent}`,
      kind: "frame",
      selection: { kind: "frame", name, value: frame.def },
      children: [],
    };
    root.children.push(node);
    byAnchor.set(name, node);
  }

  for (const [armId, arm] of armNodes) {
    const base = byAnchor.get(`arm/${armId}/base`) ?? arm;
    const flange: TreeNode = {
      id: `frame:arm/${armId}/flange`,
      label: "flange",
      secondary: "live frame",
      kind: "frame",
      selection: {
        kind: "frame",
        name: `arm/${armId}/flange`,
        value: { parent: `arm/${armId}/base`, xyz: [0, 0, 0], quat: [0, 0, 0, 1] },
      },
      children: [],
    };
    base.children.push(flange);
    byAnchor.set(`arm/${armId}/flange`, flange);

    for (const tcp of structure.tcps) {
      flange.children.push({
        id: `tcp:${armId}:${tcp.name}`,
        label: tcp.name,
        secondary: tcp.def.role,
        kind: "tcp",
        selection: { kind: "tcp", name: tcp.name, value: tcp.def },
        children: [],
      });
    }
    for (const pose of structure.poses) {
      arm.children.push({
        id: `pose:${armId}:${pose.name}`,
        label: pose.name,
        secondary: "pose",
        kind: "pose",
        selection: { kind: "pose", name: pose.name, value: pose.def },
        children: [],
      });
    }
  }

  for (const device of structure.devices.filter((item) => item.contract !== "arm")) {
    const mountArm = String(device.config?.mount_arm ?? "");
    const mount = String(device.config?.mount ?? "");
    const anchor =
      mountArm !== "" && mount !== ""
        ? byAnchor.get(`arm/${mountArm}/${mount}`)
        : undefined;
    const node: TreeNode = {
      id: `device:${device.id}`,
      label: device.id,
      secondary: device.model ?? device.contract,
      kind: "device",
      selection: { kind: "device", name: device.id, value: device },
      children: [],
    };
    (anchor ?? root).children.push(node);
  }

  for (const object of structure.objects) {
    (byAnchor.get(object.obj.frame) ?? root).children.push({
      id: `object:${object.name}`,
      label: leaf(object.name),
      secondary: object.obj.geometry.type,
      kind: "object",
      selection: { kind: "object", name: object.name, value: object.obj },
      children: [],
    });
  }

  const sort = (node: TreeNode) => {
    node.children.sort((a, b) => {
      const order: Record<NodeKind, number> = {
        world: 0,
        device: 1,
        frame: 2,
        tcp: 3,
        pose: 4,
        object: 5,
      };
      return order[a.kind] - order[b.kind] || a.label.localeCompare(b.label);
    });
    node.children.forEach(sort);
  };
  sort(root);
  return root;
}

function TreeRow({
  node,
  depth,
  selected,
  expanded,
  onToggle,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  selected: string | null;
  expanded: Set<string>;
  onToggle: (id: string) => void;
  onSelect: (selection: SceneSelection) => void;
}) {
  const Icon = ICON_BY_KIND[node.kind];
  const open = expanded.has(node.id);
  return (
    <li>
      <div
        className={`group flex h-8 items-center rounded-md pr-2 text-xs/5 transition ${
          selected === `${node.selection.kind}:${node.selection.name}`
            ? "bg-blue-500/10 text-blue-700 ring-1 ring-blue-500/20 dark:text-blue-300"
            : "text-zinc-700 hover:bg-zinc-950/5 dark:text-zinc-300 dark:hover:bg-white/5"
        }`}
        style={{ paddingLeft: 4 + depth * 14 }}
      >
        <button
          type="button"
          aria-label={`${open ? "Collapse" : "Expand"} ${node.label}`}
          disabled={node.children.length === 0}
          onClick={() => onToggle(node.id)}
          className="flex size-5 shrink-0 items-center justify-center text-zinc-400 disabled:opacity-0"
        >
          {open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
        </button>
        <button
          type="button"
          onClick={() => onSelect(node.selection)}
          title={`${node.selection.name} · ${node.kind}`}
          className="flex min-w-0 flex-1 items-center gap-1.5 text-left"
        >
          <Icon className="size-3.5 shrink-0 text-zinc-500 dark:text-zinc-400" />
          <span className="truncate font-medium text-zinc-950 dark:text-white">{node.label}</span>
          {node.secondary !== undefined && (
            <span className="ml-auto truncate text-[10px] text-zinc-400">{node.secondary}</span>
          )}
          {node.kind === "device" && (
            <CircleDot className={`size-3 shrink-0 ${node.selection.kind === "device" && node.selection.value.active !== "off" ? "text-emerald-500" : "text-zinc-300"}`} />
          )}
        </button>
      </div>
      {open && node.children.length > 0 && (
        <ul>
          {node.children.map((child) => (
            <TreeRow
              key={child.id}
              node={child}
              depth={depth + 1}
              selected={selected}
              expanded={expanded}
              onToggle={onToggle}
              onSelect={onSelect}
            />
          ))}
        </ul>
      )}
    </li>
  );
}

function FlatGroup({
  label,
  items,
  kind,
  onSelect,
}: {
  label: string;
  items: Array<{ name: string; value: unknown }>;
  kind: Exclude<NodeKind, "world">;
  onSelect: (selection: SceneSelection) => void;
}) {
  if (items.length === 0) return null;
  const Icon = ICON_BY_KIND[kind];
  return (
    <section className="mb-4">
      <h3 className="mb-1 px-2 text-[10px]/5 font-medium uppercase tracking-wider text-zinc-400">{label}</h3>
      {items.map((item) => (
        <button
          type="button"
          key={item.name}
          onClick={() => onSelect({ kind, name: item.name, value: item.value } as SceneSelection)}
          className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs/5 text-zinc-700 hover:bg-zinc-950/5 dark:text-zinc-300 dark:hover:bg-white/5"
        >
          <Icon className="size-3.5 shrink-0 text-zinc-400" />
          <span className="truncate font-medium text-zinc-950 dark:text-white">{item.name}</span>
        </button>
      ))}
    </section>
  );
}

export function SceneHierarchy({
  structure,
  selected,
  onSelect,
}: {
  structure: SceneStructure;
  selected: SceneSelection | null;
  onSelect: (selection: SceneSelection) => void;
}) {
  const [mode, setMode] = useState<"tree" | "flat">("tree");
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(["world", "device:r1", "frame:arm/r1/base", "frame:arm/r1/flange"]),
  );
  const tree = useMemo(() => makeTree(structure), [structure]);
  const selectedId =
    selected === null ? null : `${selected.kind}:${selected.name}`;
  const toggle = (id: string) =>
    setExpanded((previous) => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  return (
    <aside className="flex h-full min-h-0 flex-col bg-white dark:bg-zinc-900">
      <header className="flex h-12 shrink-0 items-center gap-2 border-b border-zinc-950/5 px-3 dark:border-white/10">
        <div className="min-w-0 flex-1">
          <h2 className="text-sm/5 font-semibold text-zinc-950 dark:text-white">Scene structure</h2>
          <p className="truncate text-[10px]/4 text-zinc-400">
            {structure.devices.length} devices · {structure.frames.length} frames · {structure.objects.length} objects
          </p>
        </div>
        <div className="flex rounded-lg bg-zinc-950/5 p-0.5 dark:bg-white/5">
          <button
            type="button"
            title="Tree mode"
            aria-pressed={mode === "tree"}
            onClick={() => setMode("tree")}
            className={`flex size-7 items-center justify-center rounded-md ${mode === "tree" ? "bg-white text-zinc-950 shadow-xs dark:bg-zinc-700 dark:text-white" : "text-zinc-400"}`}
          >
            <GitBranch className="size-3.5" />
          </button>
          <button
            type="button"
            title="Flat mode"
            aria-pressed={mode === "flat"}
            onClick={() => setMode("flat")}
            className={`flex size-7 items-center justify-center rounded-md ${mode === "flat" ? "bg-white text-zinc-950 shadow-xs dark:bg-zinc-700 dark:text-white" : "text-zinc-400"}`}
          >
            <List className="size-3.5" />
          </button>
        </div>
        <Button plain title="Refresh scene structure" onClick={() => void structure.refresh()}>
          <RefreshCw data-slot="icon" className={structure.loading ? "animate-spin" : ""} />
        </Button>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto p-2">
        {structure.error !== null && (
          <p className="mb-2 rounded-lg bg-red-500/10 p-2 text-xs/5 text-red-600 dark:text-red-400">{structure.error}</p>
        )}
        {mode === "tree" ? (
          <ul>
            <TreeRow
              node={tree}
              depth={0}
              selected={selectedId}
              expanded={expanded}
              onToggle={toggle}
              onSelect={onSelect}
            />
          </ul>
        ) : (
          <>
            <FlatGroup label="Devices" kind="device" items={structure.devices.map((item) => ({ name: item.id, value: item }))} onSelect={onSelect} />
            <FlatGroup label="Frames" kind="frame" items={structure.frames.map((item) => ({ name: item.name, value: item.def }))} onSelect={onSelect} />
            <FlatGroup label="TCPs" kind="tcp" items={structure.tcps.map((item) => ({ name: item.name, value: item.def }))} onSelect={onSelect} />
            <FlatGroup label="Poses" kind="pose" items={structure.poses.map((item) => ({ name: item.name, value: item.def }))} onSelect={onSelect} />
            <FlatGroup label="Objects" kind="object" items={structure.objects.map((item) => ({ name: item.name, value: item.obj }))} onSelect={onSelect} />
          </>
        )}
        {!structure.loading && structure.frames.length === 0 && structure.devices.length === 0 && (
          <div className="py-10 text-center text-xs/5 text-zinc-400">
            <Radio className="mx-auto mb-2 size-5" />
            Connect to load the scene structure.
          </div>
        )}
      </div>
    </aside>
  );
}
