import type { ArmStatus } from "../lib/messages";
import type { CommandCapabilities, UIMode } from "./types";

interface CapabilityInput {
  mode: UIMode;
  replay: boolean;
  connected: boolean;
  driverAlive: boolean;
  holdsControl: boolean;
  status: ArmStatus | null;
}

export function commandCapabilities({
  mode,
  replay,
  connected,
  driverAlive,
  holdsControl,
  status,
}: CapabilityInput): CommandCapabilities {
  if (replay) {
    return {
      inspect: true,
      configure: false,
      ioWrite: false,
      motion: false,
      jog: false,
      reason: "Commands are disabled in replay.",
    };
  }
  if (!connected) {
    return {
      inspect: true,
      configure: false,
      ioWrite: false,
      motion: false,
      jog: false,
      reason: "Bridge disconnected.",
    };
  }
  if (!driverAlive) {
    return {
      inspect: true,
      configure: true,
      ioWrite: false,
      motion: false,
      jog: false,
      reason: "Robot driver is stale or offline.",
    };
  }
  if (status?.estop || status?.protective_stop) {
    return {
      inspect: true,
      configure: true,
      ioWrite: false,
      motion: false,
      jog: false,
      reason: status.estop ? "Emergency stop is active." : "Protective stop is active.",
    };
  }

  const teach = mode === "teach";
  const controlReason = holdsControl ? null : "Acquire control to command the cell.";
  return {
    inspect: true,
    configure: mode === "build" || teach,
    ioWrite: holdsControl,
    motion: teach && holdsControl,
    jog: teach && holdsControl,
    reason: teach ? controlReason : "Switch to Teach mode for robot motion.",
  };
}
