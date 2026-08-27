import { Box, Cpu, Focus, Frame, GitBranch, Waypoints, X } from "lucide-react";
import { Badge } from "../catalyst/badge";
import { quatToRpyDeg } from "../lib/geometry";
import type { SceneItemSelection } from "./types";

const ICONS = {
  world: GitBranch,
  device: Cpu,
  frame: Frame,
  tcp: Focus,
  pose: Waypoints,
  object: Box,
};

function formatVector(values: number[], digits = 4): string {
  return values.map((value) => value.toFixed(digits)).join(", ");
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <>
      <dt className="text-zinc-500 dark:text-zinc-400">{label}</dt>
      <dd className="break-all text-zinc-950 dark:text-white">{value}</dd>
    </>
  );
}

export function SceneDetails({
  selection,
  onClose,
}: {
  selection: SceneItemSelection | null;
  onClose?: () => void;
}) {
  if (selection === null) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm/6 text-zinc-500 dark:text-zinc-400">
        Select a device, frame, TCP, pose, or object in the scene structure.
      </div>
    );
  }
  const Icon = ICONS[selection.kind];
  const fields: Array<[string, string]> = (() => {
    if (selection.kind === "world") {
      return [
        ["type", "root frame"],
        ["xyz", "0.0000, 0.0000, 0.0000 m"],
        ["rpy", "0.0, 0.0, 0.0°"],
      ];
    }
    if (selection.kind === "device") {
      const source = selection.value.sources.find(
        (item) => item.mode === selection.value.active,
      );
      const deviceFields: Array<[string, string]> = [
        ["contract", selection.value.contract],
        ["model", selection.value.model ?? "—"],
        ["source", selection.value.active ?? "off"],
        ["provider", source?.kind ?? "—"],
        ["launch", source?.launch ?? "—"],
      ];
      for (const [key, value] of Object.entries(selection.value.config ?? {})) {
        deviceFields.push([
          key,
          Array.isArray(value) ? value.join(", ") : String(value),
        ]);
      }
      return deviceFields;
    }
    if (selection.kind === "frame") {
      const frame = selection.value;
      const rows: [string, string][] = [
        ["parent", frame.parent],
        ["xyz", `${formatVector(frame.xyz)} m`],
        ["rpy", `${formatVector(quatToRpyDeg(frame.quat), 2)}°`],
        ["quaternion", formatVector(frame.quat)],
        ["source", frame.source ?? "—"],
      ];
      if (frame.calibration !== undefined && frame.nominal !== undefined) {
        // Calibrated: show the design value and the drift the calibration applied.
        const dx = Math.hypot(...frame.xyz.map((v, i) => v - (frame.nominal?.xyz[i] ?? v)));
        const dot = Math.abs(frame.quat.reduce((acc, v, i) => acc + v * (frame.nominal?.quat[i] ?? 0), 0));
        const dAngle = (2 * Math.acos(Math.min(1, dot)) * 180) / Math.PI;
        rows.push(
          ["nominal xyz", `${formatVector(frame.nominal.xyz)} m`],
          ["nominal rpy", `${formatVector(quatToRpyDeg(frame.nominal.quat), 2)}°`],
          ["drift", `${(dx * 1000).toFixed(2)} mm · ${dAngle.toFixed(3)}°`],
          ["calibrated", [frame.calibration.method, frame.calibration.by].filter(Boolean).join(" · ") || "yes"],
        );
        if (typeof frame.calibration.residual === "number") {
          rows.push(["residual", String(frame.calibration.residual)]);
        }
      }
      rows.push(["revision", String(frame.revision ?? "—")]);
      return rows;
    }
    if (selection.kind === "tcp") {
      return [
        ["role", selection.value.role],
        ["selectable", selection.value.selectable_as_tcp ? "yes" : "no"],
        ["xyz", `${formatVector(selection.value.xyz)} m`],
        ["rpy", `${formatVector(quatToRpyDeg(selection.value.quat), 2)}°`],
        ["quaternion", formatVector(selection.value.quat)],
        ["revision", String(selection.value.revision ?? "—")],
      ];
    }
    if (selection.kind === "pose") {
      return [
        [
          "joints",
          `${formatVector(selection.value.q.map((value) => value * 180 / Math.PI), 2)}°`,
        ],
        ["revision", String(selection.value.revision ?? "—")],
      ];
    }
    const geometry = selection.value.geometry;
    return [
      ["frame", selection.value.frame],
      ["geometry", geometry.type],
      ["asset", geometry.uri ?? "—"],
      ["xyz", `${formatVector(selection.value.pose.xyz)} m`],
      ["rpy", `${formatVector(quatToRpyDeg(selection.value.pose.quat), 2)}°`],
      ["revision", String(selection.value.revision ?? "—")],
    ];
  })();

  return (
    <aside className="flex h-full min-h-0 flex-col bg-white dark:bg-zinc-900">
      <header className="border-b border-zinc-950/5 px-4 py-3 dark:border-white/10">
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-zinc-500 dark:text-zinc-400" />
          <h2 className="min-w-0 flex-1 truncate text-sm/6 font-semibold text-zinc-950 dark:text-white">
            {selection.name === "world" ? "World" : selection.name}
          </h2>
          <Badge color="zinc">{selection.kind}</Badge>
          {onClose !== undefined && (
            <button
              type="button"
              aria-label="Close scene item details"
              title="Return to active tool"
              onClick={onClose}
              className="flex size-7 items-center justify-center rounded-md text-zinc-400 hover:bg-zinc-950/5 hover:text-zinc-950 dark:hover:bg-white/10 dark:hover:text-white"
            >
              <X className="size-4" />
            </button>
          )}
        </div>
        <p className="mt-0.5 text-xs/5 text-zinc-500 dark:text-zinc-400">
          Scene item details
        </p>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 font-mono text-xs/5">
          {fields.map(([label, value]) => (
            <Field key={label} label={label} value={value} />
          ))}
        </dl>
      </div>
    </aside>
  );
}
