import { createContext, useContext, type RefObject } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import type { BrowserProducerState } from "../lib/camera2d/producer";
import type { Realm } from "../lib/config";
import type {
  ArmStatus,
  ControlOwnerState,
  FlangeState,
  IoState,
  JointState,
  DevicesList,
} from "../lib/messages";

export interface RuntimeState {
  url: string;
  setUrl: (url: string) => void;
  session: Session | null;
  connecting: boolean;
  connectError: string | null;
  connect: () => Promise<void>;
  realm: Realm;
  setRealm: (realm: Realm) => void;
  prefix: string | null;
  replaySessions: string[];
  io: IoState | null;
  /** The supervisor's device inventory (cell realms only). */
  devices: DevicesList | null;
  status: ArmStatus | null;
  wsConnected: boolean;
  driverAlive: boolean;
  commandsEnabled: boolean;
  safetyActive: boolean;
  controlOwner: ControlOwnerState | null;
  clientId: string;
  holdsControl: boolean;
  acquire: () => void;
  release: () => void;
  jointsRef: RefObject<JointState | null>;
  jointsCountRef: RefObject<number>;
  flangeRef: RefObject<FlangeState | null>;
  cameraProducer: BrowserProducerState;
}

export const RuntimeContext = createContext<RuntimeState | null>(null);

export function useRuntime(): RuntimeState {
  const runtime = useContext(RuntimeContext);
  if (runtime === null) throw new Error("useRuntime must be used inside RuntimeProvider");
  return runtime;
}
