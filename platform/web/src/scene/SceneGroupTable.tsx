import {
  Box,
  Cpu,
  Focus,
  Frame,
  Plus,
  Waypoints,
  X,
} from "lucide-react";
import { Button } from "../catalyst/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
} from "../catalyst/table";
import { quatToRpyDeg } from "../lib/geometry";
import { SortableHeader } from "../table/SortableHeader";
import {
  applyControls,
  type CellValue,
  useTableControls,
} from "../table/useTableControls";
import type {
  SceneCreateKind,
  SceneGroupKind,
  SceneItemSelection,
} from "./types";
import type { SceneStructure } from "./useSceneStructure";

interface GroupRow {
  key: string;
  selection: SceneItemSelection;
  values: Record<string, CellValue>;
}

const GROUP_META: Record<
  SceneGroupKind,
  {
    label: string;
    icon: typeof Box;
    createKind: SceneCreateKind | null;
    columns: Array<{ key: string; label: string }>;
  }
> = {
  devices: {
    label: "Devices",
    icon: Cpu,
    createKind: null,
    columns: [
      { key: "name", label: "Name" },
      { key: "contract", label: "Contract" },
      { key: "model", label: "Model" },
      { key: "active", label: "Source" },
    ],
  },
  frames: {
    label: "Frames",
    icon: Frame,
    createKind: "frame",
    columns: [
      { key: "name", label: "Name" },
      { key: "parent", label: "Parent" },
      { key: "xyz", label: "XYZ (m)" },
      { key: "rpy", label: "RPY (deg)" },
    ],
  },
  tcps: {
    label: "TCPs",
    icon: Focus,
    createKind: "tcp",
    columns: [
      { key: "name", label: "Name" },
      { key: "role", label: "Role" },
      { key: "xyz", label: "XYZ (m)" },
      { key: "rpy", label: "RPY (deg)" },
    ],
  },
  poses: {
    label: "Poses",
    icon: Waypoints,
    createKind: "pose",
    columns: [
      { key: "name", label: "Name" },
      { key: "joints", label: "Joints (deg)" },
    ],
  },
  objects: {
    label: "Objects",
    icon: Box,
    createKind: "object",
    columns: [
      { key: "name", label: "Name" },
      { key: "frame", label: "Frame" },
      { key: "geometry", label: "Geometry" },
      { key: "asset", label: "Asset / size" },
    ],
  },
};

const vector = (values: number[], digits = 3) =>
  values.map((value) => value.toFixed(digits)).join(", ");

function rowsFor(structure: SceneStructure, group: SceneGroupKind): GroupRow[] {
  if (group === "devices") {
    return structure.devices.map((value) => ({
      key: value.id,
      selection: { kind: "device", name: value.id, value },
      values: {
        name: value.id,
        contract: value.contract,
        model: value.model,
        active: value.active ?? "off",
      },
    }));
  }
  if (group === "frames") {
    return structure.frames.map(({ name, def: value }) => ({
      key: name,
      selection: { kind: "frame", name, value },
      values: {
        name,
        parent: value.parent,
        xyz: vector(value.xyz),
        rpy: vector(quatToRpyDeg(value.quat), 1),
      },
    }));
  }
  if (group === "tcps") {
    return structure.tcps.map(({ name, def: value }) => ({
      key: name,
      selection: { kind: "tcp", name, value },
      values: {
        name,
        role: value.role,
        xyz: vector(value.xyz),
        rpy: vector(quatToRpyDeg(value.quat), 1),
      },
    }));
  }
  if (group === "poses") {
    return structure.poses.map(({ name, def: value }) => ({
      key: name,
      selection: { kind: "pose", name, value },
      values: {
        name,
        joints: vector(value.q.map((joint) => (joint * 180) / Math.PI), 1),
      },
    }));
  }
  return structure.objects.map(({ name, obj: value }) => ({
    key: name,
    selection: { kind: "object", name, value },
    values: {
      name,
      frame: value.frame,
      geometry: value.geometry.type,
      asset:
        value.geometry.uri ??
        (value.geometry.size !== undefined
          ? vector(value.geometry.size)
          : value.geometry.radius ?? "—"),
    },
  }));
}

export function SceneGroupTable({
  group,
  structure,
  onSelect,
  onCreate,
  onClose,
}: {
  group: SceneGroupKind;
  structure: SceneStructure;
  onSelect: (selection: SceneItemSelection) => void;
  onCreate: (kind: SceneCreateKind) => void;
  onClose: () => void;
}) {
  const controls = useTableControls();
  const meta = GROUP_META[group];
  const Icon = meta.icon;
  const rows = rowsFor(structure, group);
  const shown = applyControls(
    rows,
    controls,
    (row, column) => row.values[column] ?? null,
  );

  return (
    <aside className="flex h-full min-h-0 flex-col bg-white dark:bg-zinc-900">
      <header className="flex shrink-0 items-start gap-2 border-b border-zinc-950/5 px-4 py-3 dark:border-white/10">
        <Icon className="mt-1 size-4 text-zinc-500 dark:text-zinc-400" />
        <div className="min-w-0 flex-1">
          <h2 className="text-sm/6 font-semibold text-zinc-950 dark:text-white">
            {meta.label}
          </h2>
          <p className="text-xs/5 text-zinc-500 dark:text-zinc-400">
            {rows.length} configured {rows.length === 1 ? "entry" : "entries"}
          </p>
        </div>
        {meta.createKind !== null ? (
          <Button
            plain
            aria-label={`Add ${meta.createKind}`}
            onClick={() => onCreate(meta.createKind!)}
          >
            <Plus data-slot="icon" />
          </Button>
        ) : (
          <Button
            plain
            disabled
            aria-label="Devices are declared in cell.yaml"
            title="Devices are declared in deploy/cell.yaml"
          >
            <Plus data-slot="icon" />
          </Button>
        )}
        <Button plain aria-label={`Close ${meta.label}`} onClick={onClose}>
          <X data-slot="icon" />
        </Button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto p-4 [--gutter:--spacing(2)]">
        {controls.hasActiveFilters && (
          <Button plain onClick={controls.clearAll}>
            Clear filters and sorting
          </Button>
        )}
        <Table dense grid className="mt-2 text-xs">
          <TableHead>
            <TableRow>
              {meta.columns.map((column) => (
                <SortableHeader
                  key={column.key}
                  column={column.key}
                  label={column.label}
                  sort={controls.sort}
                  onToggleSort={controls.toggleSort}
                  filter={controls.filters[column.key]}
                  onSetFilter={controls.setFilter}
                />
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {shown.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={meta.columns.length}
                  className="py-8 text-center text-zinc-500 dark:text-zinc-400"
                >
                  {rows.length === 0
                    ? `No ${meta.label.toLocaleLowerCase()} configured.`
                    : "No entries match the active filters."}
                </TableCell>
              </TableRow>
            ) : (
              shown.map((row) => (
                <TableRow
                  key={row.key}
                  title={`Open ${row.key}`}
                  onClick={() => onSelect(row.selection)}
                  className="cursor-pointer hover:bg-zinc-950/5 dark:hover:bg-white/5"
                >
                  {meta.columns.map((column, index) => (
                    <TableCell
                      key={column.key}
                      className={index === 0 ? "font-medium" : "text-zinc-600 dark:text-zinc-300"}
                    >
                      {String(row.values[column.key] ?? "—")}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </aside>
  );
}
