import { useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import CamerasPage from "../pages/CamerasPage";
import IoPage from "../pages/IoPage";
import { configSet } from "../lib/actions";
import { configFrame } from "../lib/config";
import type {
  ArmStatus,
  FrameDef,
  IoState,
  TcpState,
} from "../lib/messages";
import type {
  CommandCapabilities,
  Selection,
  UIMode,
} from "./types";

export function WorkspaceHeader({
  eyebrow,
  title,
  description,
  onClose,
}: {
  eyebrow: string;
  title: string;
  description: string;
  onClose: () => void;
}) {
  return (
    <header className="mb-5 flex items-start justify-between gap-4">
      <div>
        <p className="spatial-eyebrow">{eyebrow}</p>
        <h2 className="mt-1 text-2xl font-semibold">{title}</h2>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[var(--shell-muted)]">
          {description}
        </p>
      </div>
      <button type="button" className="spatial-button" onClick={onClose}>
        Close
      </button>
    </header>
  );
}

export function CameraWorkspace({
  session,
  realm,
  connected,
  capabilities,
}: {
  session: Session | null;
  realm: string | null;
  connected: boolean;
  capabilities: CommandCapabilities;
}) {
  if (realm === null) return <WorkspaceEmpty text="Select a replay session." />;
  return (
    <div className="spatial-legacy-embed h-[calc(100%-88px)] min-h-[420px]">
      <CamerasPage
        session={session}
        realm={realm}
        wsConnected={connected}
        commandsEnabled={capabilities.configure}
      />
    </div>
  );
}

export function IoWorkspace({
  session,
  realm,
  io,
  connected,
  capabilities,
}: {
  session: Session | null;
  realm: string | null;
  io: IoState | null;
  connected: boolean;
  capabilities: CommandCapabilities;
}) {
  if (realm === null) return <WorkspaceEmpty text="Select a replay session." />;
  return (
    <div className="spatial-legacy-embed h-[calc(100%-88px)] min-h-[360px]">
      <IoPage
        session={session}
        realm={realm}
        io={io}
        wsConnected={connected}
        commandsEnabled={capabilities.ioWrite}
      />
      {!capabilities.ioWrite && (
        <p className="spatial-notice mt-3">{capabilities.reason}</p>
      )}
    </div>
  );
}

export function FrameWorkspace({
  session,
  frameId,
  frame,
  tcp,
  capabilities,
}: {
  session: Session | null;
  frameId: string;
  frame: FrameDef | null;
  tcp: TcpState | null;
  capabilities: CommandCapabilities;
}) {
  const [name, setName] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const createFromTcp = async () => {
    const nextName = name.trim();
    if (
      session === null ||
      tcp === null ||
      nextName === "" ||
      !capabilities.configure
    ) {
      return;
    }
    setPending(true);
    setMessage(null);
    try {
      const reply = await configSet(session, configFrame(nextName), {
        parent: tcp.pose.frame,
        xyz: tcp.pose.xyz,
        quat: tcp.pose.quat,
        source: "teach/current_tcp",
        meta: { created_by: "spatial-ui" },
      });
      if (!reply.ok) throw new Error(reply.error ?? "Frame creation failed.");
      setMessage(`Created ${nextName} at revision ${reply.revision ?? "unknown"}.`);
      setName("");
    } catch (cause) {
      setMessage(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="space-y-4">
      <section className="spatial-section">
        <p className="spatial-eyebrow">Selected frame</p>
        <h3 className="mt-1 text-lg font-semibold">{frameId}</h3>
        {frame === null ? (
          <p className="mt-3 text-sm text-[var(--shell-muted)]">
            No frame definition is available.
          </p>
        ) : (
          <div className="mt-4 grid grid-cols-2 gap-3">
            <EngineeringValue label="Parent" value={frame.parent} />
            <EngineeringValue
              label="Revision"
              value={String(frame.revision ?? "-")}
            />
            <EngineeringValue
              label="Position"
              value={frame.xyz.map((value) => `${(value * 1000).toFixed(2)} mm`).join(" / ")}
            />
            <EngineeringValue
              label="Quaternion"
              value={frame.quat.map((value) => value.toFixed(5)).join(" / ")}
            />
            <EngineeringValue label="Source" value={frame.source ?? "manual"} />
          </div>
        )}
      </section>

      <section className="spatial-section">
        <p className="spatial-eyebrow">Teach command</p>
        <h3 className="mt-1 text-lg font-semibold">Create from current TCP</h3>
        <p className="mt-2 text-sm leading-6 text-[var(--shell-muted)]">
          Capture the current controlled point as a child of its reported frame.
        </p>
        <div className="mt-4 flex gap-2">
          <input
            className="spatial-input flex-1"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="frame name"
          />
          <button
            type="button"
            className="spatial-button-primary"
            disabled={
              pending ||
              name.trim() === "" ||
              tcp === null ||
              !capabilities.configure
            }
            onClick={() => void createFromTcp()}
          >
            {pending ? "Creating..." : "Create frame"}
          </button>
        </div>
        {!capabilities.configure && (
          <p className="spatial-notice mt-3">{capabilities.reason}</p>
        )}
        {tcp === null && (
          <p className="spatial-notice mt-3">
            Waiting for a live TCP sample before capture.
          </p>
        )}
        {message !== null && <p className="mt-3 text-sm">{message}</p>}
      </section>
    </div>
  );
}

export function SceneWorkspace({
  mode,
  selection,
  status,
}: {
  mode: UIMode;
  selection: Selection | null;
  status: ArmStatus | null;
}) {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <WorkspaceCard
        label="Current intent"
        value={
          mode === "teach"
            ? "Position and teach the cell with explicit control ownership."
            : "Inspect live cell state without exposing motion controls."
        }
      />
      <WorkspaceCard
        label="Selection"
        value={selection?.label ?? "Nothing selected"}
      />
      <WorkspaceCard
        label="Robot mode"
        value={status?.mode ?? "No status sample"}
      />
      <WorkspaceCard
        label="Interaction model"
        value="Select in the scene or tree, use the compact context card, and open this workspace only for deeper work."
      />
    </div>
  );
}

export function UiLab() {
  return (
    <div className="spatial-root spatial-grid spatial-scrollbar min-h-full overflow-auto p-6">
      <p className="spatial-eyebrow">Spatial UI lab</p>
      <h1 className="mt-2 text-3xl font-semibold">Commissioning interface kit</h1>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--shell-muted)]">
        The lab renders operational states with the same tokens and components as
        the application. Use it to review intent, contrast, density, and failure
        states without connecting to a cell.
      </p>
      <div className="mt-8 grid gap-5 lg:grid-cols-2">
        <section className="spatial-panel rounded-[28px] p-5">
          <p className="spatial-eyebrow">Status hierarchy</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <LabChip label="Safety OK" tone="ok" />
            <LabChip label="Protective stop" tone="warn" />
            <LabChip label="Emergency stop" tone="danger" />
            <LabChip label="Replay" tone="muted" />
          </div>
        </section>
        <section className="spatial-panel rounded-[28px] p-5">
          <p className="spatial-eyebrow">Commands</p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className="spatial-button-primary">
              Acquire control
            </button>
            <button type="button" className="spatial-button">
              Open details
            </button>
            <button type="button" className="spatial-stop">
              Stop motion
            </button>
            <button type="button" className="spatial-button" disabled>
              Disabled
            </button>
          </div>
        </section>
        <section className="spatial-panel rounded-[28px] p-5">
          <p className="spatial-eyebrow">Engineering values</p>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <EngineeringValue label="TCP X" value="423.18 mm" />
            <EngineeringValue label="Speed" value="20%" />
            <EngineeringValue label="Exposure" value="8,000 us" />
            <EngineeringValue label="Confidence" value="0.92" />
          </div>
        </section>
        <section className="spatial-panel rounded-[28px] p-5">
          <p className="spatial-eyebrow">Failure states</p>
          <p className="spatial-notice mt-4">Driver heartbeat is stale.</p>
          <p className="spatial-error mt-3">Motion rejected: control lease lost.</p>
        </section>
      </div>
    </div>
  );
}

function WorkspaceCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="spatial-section">
      <p className="spatial-eyebrow">{label}</p>
      <p className="mt-2 text-sm leading-6">{value}</p>
    </div>
  );
}

function EngineeringValue({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="spatial-value">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function WorkspaceEmpty({ text }: { text: string }) {
  return <p className="spatial-notice">{text}</p>;
}

function LabChip({
  label,
  tone,
}: {
  label: string;
  tone: "ok" | "warn" | "danger" | "muted";
}) {
  return <span className={`spatial-chip spatial-chip-${tone}`}>{label}</span>;
}
