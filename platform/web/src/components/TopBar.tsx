// Top bar (spec §2): cell identity + WS connection dot, CELL/REPLAY namespace
// switcher, safety cluster + control-lease chip, namespace name in small caps.
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { cn } from "@/lib/utils";
import { CELL_NAME, type Realm, type RealmKind } from "../lib/config";
import type { ArmStatus, ControlOwnerState } from "../lib/messages";

interface TopBarProps {
  realm: Realm;
  onRealmChange: (r: Realm) => void;
  wsConnected: boolean;
  status: ArmStatus | null;
  replaySessions: string[];
  url: string;
  onUrlChange: (u: string) => void;
  onConnect: () => void;
  connecting: boolean;
  connectError: string | null;
  controlOwner: ControlOwnerState | null;
  holdsControl: boolean;
  commandsEnabled: boolean;
  driverAlive: boolean;
  onAcquire: () => void;
  onRelease: () => void;
}

const REALM_ITEM_CLASS =
  "px-3 text-xs font-semibold tracking-wider data-[state=on]:bg-primary data-[state=on]:text-primary-foreground";

export default function TopBar({
  realm,
  onRealmChange,
  wsConnected,
  status,
  replaySessions,
  url,
  onUrlChange,
  onConnect,
  connecting,
  connectError,
  controlOwner,
  holdsControl,
  commandsEnabled,
  driverAlive,
  onAcquire,
  onRelease,
}: TopBarProps) {
  // Tick once a second so the lease countdown decrements between owner
  // republishes (the driver keepalive is 1 Hz; expires_at only moves on renew).
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const pickRealm = (kind: RealmKind) => {
    if (kind === realm.kind) return;
    if (kind === "replay") {
      onRealmChange({
        kind: "replay",
        replaySession: replaySessions.length === 1 ? replaySessions[0] : null,
      });
      return;
    }
    onRealmChange({ kind: "cell", replaySession: null });
  };

  const owner = controlOwner?.owner ?? null;
  const leaseEnabled = commandsEnabled && driverAlive;
  const msLeft =
    owner === null ? 0 : Number(BigInt(owner.expires_at) / 1_000_000n) - now;
  const secLeft = Math.max(0, Math.floor(msLeft / 1000));
  const countdown = `${Math.floor(secLeft / 60)}:${String(secLeft % 60).padStart(2, "0")}`;

  const safetyStop = status?.estop === true || status?.protective_stop === true;

  return (
    <header className="col-span-2 flex items-center gap-3 border-b border-border bg-card px-3 py-1.5">
      <span className="flex items-center gap-2 text-sm font-semibold">
        ⬡ {CELL_NAME}
        <span
          title={wsConnected ? "bridge connected" : "bridge disconnected"}
          className={cn(
            "inline-block size-2 rounded-full",
            wsConnected ? "bg-ok" : "bg-destructive",
          )}
        />
      </span>
      <Input
        className="w-56"
        value={url}
        spellCheck={false}
        onChange={(e) => onUrlChange(e.target.value)}
      />
      <Button onClick={onConnect} disabled={connecting}>
        {connecting ? "Connecting…" : "Connect"}
      </Button>
      {connectError !== null && (
        <span className="text-xs text-destructive">{connectError}</span>
      )}

      <div className="flex flex-1 items-center justify-center gap-3">
        <ToggleGroup
          type="single"
          value={realm.kind}
          onValueChange={(v) => {
            if (v) pickRealm(v as RealmKind);
          }}
        >
          <ToggleGroupItem value="cell" className={REALM_ITEM_CLASS}>
            CELL
          </ToggleGroupItem>
          <ToggleGroupItem value="replay" className={REALM_ITEM_CLASS}>
            REPLAY
          </ToggleGroupItem>
        </ToggleGroup>
        <span className="text-xs uppercase tracking-widest text-[var(--tint)]">
          {realm.kind}
        </span>
      </div>

      <div className="flex items-center gap-3">
        <span
          className={cn(
            "text-xs",
            status?.servo_on ? "text-ok" : "text-muted-foreground",
          )}
        >
          ●servo
        </span>
        {status === null ? (
          <Badge variant="secondary">—</Badge>
        ) : safetyStop ? (
          <Badge variant="destructive">
            {status.estop ? "E-STOP" : "P-STOP"}
          </Badge>
        ) : (
          <Badge variant="secondary">SAFE</Badge>
        )}
        <span className="font-mono text-xs tabular-nums">
          spd {status === null ? "—" : `${Math.round(status.speed_scale * 100)}%`}
        </span>
        <button
          type="button"
          disabled={!leaseEnabled && !holdsControl}
          onClick={() => {
            if (holdsControl) onRelease();
            else if (leaseEnabled) onAcquire();
          }}
          title={
            holdsControl
              ? "You hold control — click to release"
              : owner !== null
                ? `Held by ${owner.user}`
                : "Request control"
          }
          className={cn(
            "rounded border px-2 py-0.5 text-xs font-medium tabular-nums transition-colors disabled:opacity-50",
            holdsControl
              ? "border-ok/40 bg-ok/10 text-ok"
              : owner !== null
                ? "border-amber-500/40 bg-amber-500/10 text-amber-400"
                : "border-border text-muted-foreground hover:bg-accent",
          )}
        >
          {owner === null
            ? "— no one in control —"
            : `${holdsControl ? "" : "🔒 "}${owner.user} · ${countdown} left`}
        </button>
      </div>
    </header>
  );
}
