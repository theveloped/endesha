// IO page (program-layer RFC §7.2): one channel table per `dio` device in the
// inventory. Named channels (cell.yaml `channels:`) come first; every physical
// point nobody named is listed below as an auto channel (`di3`, `tool_do0`, …)
// so the raw bank stays visible. The address column shows the pin behind each
// name. Outputs are toggled/typed via cmd/set; ANY channel can be forced via
// cmd/force (PLC semantics) — a forced channel reports the forced value
// regardless of the source, which is how inputs are driven in sim.
// No optimistic update: rows render the state stream, never the click — a
// failed write is visible as a control that snaps back. Both commands are
// gated by the cell-level control lease.
import { useEffect, useMemo, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { Lock, LockOpen } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { dioForce, dioSet } from "../lib/actions";
import { subscribeLatest, type Unsubscribe } from "../lib/bus";
import { dioStateChannels } from "../lib/config";
import type {
  ChannelDecl,
  ChannelsState,
  ChannelValue,
  DeviceEntry,
} from "../lib/messages";

interface IoPageProps {
  session: Session | null;
  realm: string;
  devices: DeviceEntry[];
  wsConnected: boolean;
  commandsEnabled: boolean;
  clientId: string;
  holdsControl: boolean;
}

const KIND_LABEL: Record<string, string> = {
  di: "DI",
  do: "DO",
  ai: "AI",
  ao: "AO",
};

function addressLabel(address: Record<string, unknown> | undefined): string {
  if (address === undefined) return "";
  const bank = address.bank;
  const pin = address.pin ?? address.index;
  if (pin !== undefined) {
    return `${typeof bank === "string" && bank !== "standard" ? `${bank} ` : ""}${String(pin)}`;
  }
  return Object.entries(address)
    .map(([k, v]) => `${k}=${String(v)}`)
    .join(" ");
}

function declAddress(decl: ChannelDecl | undefined): Record<string, unknown> | undefined {
  if (decl === undefined) return undefined;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(decl)) {
    if (k === "kind" || k === "unit" || k === "scale" || k === "offset") continue;
    out[k] = v;
  }
  return out;
}

/** One table row's static description: from cell config (named) or from the
 *  provider's state (auto/unmapped point). */
interface Row {
  name: string;
  kind: string;
  unit?: string;
  address?: Record<string, unknown>;
  auto: boolean;
}

function formatValue(cv: ChannelValue | undefined, unit: string | undefined): string {
  if (cv === undefined) return "—";
  if (typeof cv.value === "boolean") return cv.value ? "ON" : "off";
  const n = Number(cv.value);
  return `${Number.isFinite(n) ? n.toFixed(3) : String(cv.value)}${unit ? ` ${unit}` : ""}`;
}

function DioDeviceCard({
  session,
  realm,
  device,
  canCommand,
  clientId,
}: {
  session: Session | null;
  realm: string;
  device: DeviceEntry;
  canCommand: boolean;
  clientId: string;
}) {
  const [state, setState] = useState<ChannelsState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const decls = useMemo(
    () => ((device.config?.channels ?? {}) as Record<string, ChannelDecl>),
    [device.config],
  );
  // Named rows from the cell config (stable even before the first state
  // sample); auto rows from the provider's state (it knows its physical points).
  const named = useMemo<Row[]>(
    () =>
      Object.entries(decls).map(([name, decl]) => ({
        name,
        kind: decl.kind,
        unit: decl.unit,
        address: declAddress(decl),
        auto: false,
      })),
    [decls],
  );
  const unmapped = useMemo<Row[]>(
    () =>
      Object.entries(state?.channels ?? {})
        .filter(([name, cv]) => cv.auto === true && !(name in decls))
        .map(([name, cv]) => ({ name, kind: cv.kind, address: cv.address, auto: true })),
    [state, decls],
  );

  useEffect(() => {
    setState(null);
    if (session === null || device.active === null || device.active === "off") return;
    let disposed = false;
    let unsubscribe: Unsubscribe | null = null;
    void (async () => {
      const next = await subscribeLatest(
        session,
        dioStateChannels(realm, device.id),
        (message) => setState(message as ChannelsState),
        4,
      );
      if (disposed) next();
      else unsubscribe = next;
    })();
    return () => {
      disposed = true;
      unsubscribe?.();
    };
  }, [session, realm, device.id, device.active]);

  const run = async (label: string, fn: () => Promise<{ ok: boolean; error: string | null }>) => {
    if (session === null) return;
    setError(null);
    try {
      const ack = await fn();
      if (!ack.ok) setError(`${label}: ${ack.error ?? "failed"}`);
    } catch (e) {
      setError(`${label}: ${String(e)}`);
    }
  };

  const setOutput = (name: string, value: boolean | number) =>
    run(`set ${name}`, () => dioSet(session!, realm, device.id, clientId, name, value));
  const force = (name: string, value: boolean | number | null) =>
    run(`force ${name}`, () => dioForce(session!, realm, device.id, clientId, name, value));

  const alive = state !== null;

  const renderRow = (row: Row) => {
    const { name } = row;
    const cv = state?.channels[name];
    const isOutput = row.kind === "do" || row.kind === "ao";
    const isDigital = row.kind === "di" || row.kind === "do";
    const forced = cv?.forced === true;
    const on = cv !== undefined && cv.value === true;
    const controlsOn = canCommand && alive;
    return (
      <tr
        key={name}
        className={cn(
          "border-t border-border/60 [&>td]:py-1 [&>td]:align-middle",
          forced && "bg-amber-500/10",
          row.auto && "text-muted-foreground",
        )}
      >
        <td className="font-mono">{name}</td>
        <td>
          <span className="text-xs text-muted-foreground">{KIND_LABEL[row.kind] ?? row.kind}</span>
        </td>
        <td>
          <span className="font-mono text-xs text-muted-foreground">{addressLabel(row.address)}</span>
        </td>
        <td>
          <span
            className={cn(
              "inline-flex min-w-16 items-center gap-1 rounded-md border px-1.5 font-mono text-xs tabular-nums",
              isDigital && on
                ? "border-ok bg-ok/20 text-ok"
                : "border-border text-muted-foreground",
              forced && "border-amber-500 text-amber-600 dark:text-amber-400",
            )}
          >
            {formatValue(cv, row.unit)}
            {forced && <span className="text-[10px] uppercase">forced</span>}
          </span>
        </td>
        <td>
          {isDigital ? (
            <Button
              variant="outline"
              size="sm"
              className="cmd h-7 px-2"
              disabled={!controlsOn || (isOutput && forced)}
              onClick={() => void (isOutput ? setOutput(name, !on) : force(name, !on))}
              title={
                isOutput
                  ? forced
                    ? "Output is forced; clear the force to set it"
                    : `Set ${name} ${on ? "off" : "ON"}`
                  : `Force input ${name} ${on ? "off" : "ON"}`
              }
            >
              {isOutput ? (on ? "turn off" : "turn on") : on ? "force off" : "force on"}
            </Button>
          ) : (
            <form
              className="flex items-center gap-1"
              onSubmit={(event) => {
                event.preventDefault();
                const raw = drafts[name];
                const parsed = Number(raw);
                if (raw === undefined || raw === "" || !Number.isFinite(parsed)) return;
                void (isOutput && !forced ? setOutput(name, parsed) : force(name, parsed));
              }}
            >
              <Input
                value={drafts[name] ?? ""}
                placeholder={isOutput ? "value" : "force value"}
                className="h-7 w-24 font-mono text-xs"
                disabled={!controlsOn}
                onChange={(event) =>
                  setDrafts((current) => ({ ...current, [name]: event.target.value }))
                }
              />
              <Button type="submit" variant="outline" size="sm" className="cmd h-7 px-2" disabled={!controlsOn}>
                {isOutput && !forced ? "set" : "force"}
              </Button>
            </form>
          )}
        </td>
        <td>
          {forced ? (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0 text-amber-600 dark:text-amber-400"
              disabled={!controlsOn}
              title={`Clear force on ${name}`}
              onClick={() => void force(name, null)}
            >
              <Lock className="size-3.5" />
            </Button>
          ) : (
            <span
              className="inline-flex h-7 w-7 items-center justify-center text-muted-foreground/40"
              title="not forced"
            >
              <LockOpen className="size-3.5" />
            </span>
          )}
        </td>
      </tr>
    );
  };

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="font-mono">{device.id}</span>
          <span className="text-xs font-normal text-muted-foreground">
            {device.model ?? "dio"} · {device.active ?? "off"}
            {device.provided_by !== undefined && ` · via ${device.provided_by}`}
          </span>
          <Badge variant={alive ? "secondary" : "outline"} className="ml-auto">
            {device.active === "off" ? "off" : alive ? "live" : "no state"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {named.length === 0 && unmapped.length === 0 ? (
          <p className="text-sm text-muted-foreground">no channels declared</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-xs text-muted-foreground">
              <tr className="[&>th]:py-1 [&>th]:text-left [&>th]:font-medium">
                <th>Channel</th>
                <th className="w-10">Kind</th>
                <th className="w-16" title="Provider address (bank / pin / index)">Pin</th>
                <th className="w-28">Value</th>
                <th>Control</th>
                <th className="w-8" title="Force (override reported value)" />
              </tr>
            </thead>
            <tbody>
              {named.map((row) => renderRow(row))}
              {unmapped.length > 0 && (
                <tr>
                  <td colSpan={6} className="pt-3 pb-1 text-xs font-medium tracking-wide text-muted-foreground">
                    UNMAPPED PINS
                    <span className="ml-2 font-normal">
                      raw points without a name in cell.yaml ({unmapped.length})
                    </span>
                  </td>
                </tr>
              )}
              {unmapped.map((row) => renderRow(row))}
            </tbody>
          </table>
        )}
        {error !== null && <p className="mt-2 text-sm text-destructive">{error}</p>}
      </CardContent>
    </Card>
  );
}

export default function IoPage({
  session,
  realm,
  devices,
  wsConnected,
  commandsEnabled,
  clientId,
  holdsControl,
}: IoPageProps) {
  const dioDevices = useMemo(
    () => devices.filter((device) => device.contract === "dio"),
    [devices],
  );
  const canCommand = wsConnected && commandsEnabled && holdsControl;

  return (
    <div className="h-full space-y-2 overflow-y-auto p-2">
      {!holdsControl && wsConnected && (
        <p className="px-1 text-xs text-muted-foreground">
          Request control to set outputs or force channels.
        </p>
      )}
      {dioDevices.length === 0 ? (
        <Card size="sm">
          <CardContent>
            <p className="text-sm text-muted-foreground">
              No IO devices in this cell. Declare a <span className="font-mono">dio</span> resource with
              named <span className="font-mono">channels</span> in cell.yaml.
            </p>
          </CardContent>
        </Card>
      ) : (
        dioDevices.map((device) => (
          <DioDeviceCard
            key={device.id}
            session={session}
            realm={realm}
            device={device}
            canCommand={canCommand}
            clientId={clientId}
          />
        ))
      )}
    </div>
  );
}
