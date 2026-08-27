// PackML unit vocabulary mirrored from wf/services/program_runner/unit.py so
// the UI can enable exactly the commands the runner would accept in a state.
import type { UnitCommand } from "./config";
import type { UnitState } from "./messages";

const STOPPABLE: UnitState[] = [
  "idle", "starting", "execute", "completing", "complete",
  "holding", "held", "unholding", "suspending", "suspended", "unsuspending", "resetting",
];
const ABORTABLE: UnitState[] = [...STOPPABLE, "stopping", "stopped", "clearing"];

export function unitAccepts(unit: UnitState | null, command: UnitCommand): boolean {
  if (unit === null) return false;
  switch (command) {
    case "start":
      return unit === "idle";
    case "hold":
    case "suspend":
      return unit === "execute";
    case "unhold":
      return unit === "held";
    case "unsuspend":
      return unit === "suspended";
    case "stop":
      return STOPPABLE.includes(unit);
    case "abort":
      return ABORTABLE.includes(unit);
    case "clear":
      return unit === "aborted";
    case "reset":
      return unit === "stopped" || unit === "complete";
    case "unload":
      return unit === "idle" || unit === "stopped";
  }
}

/** Badge colour family per unit state (catalyst Badge `color` values). */
export function unitTone(unit: UnitState | null): "zinc" | "emerald" | "amber" | "red" | "blue" | "sky" {
  switch (unit) {
    case "execute":
      return "emerald";
    case "starting":
    case "completing":
    case "unholding":
    case "unsuspending":
    case "resetting":
    case "clearing":
      return "sky";
    case "held":
    case "holding":
    case "suspended":
    case "suspending":
      return "amber";
    case "aborting":
    case "aborted":
      return "red";
    case "stopping":
    case "stopped":
      return "amber";
    case "complete":
      return "blue";
    default:
      return "zinc";
  }
}

/** Human label; the wire value is the PackML lowercase id. */
export function unitLabel(unit: UnitState | null): string {
  if (unit === null) return "NO RUNNER";
  return unit.toUpperCase();
}
