// IO page (program-layer RFC §7.2): one channel table per `dio` device in the
// inventory. Channels are NAMED (cell.yaml `channels:`); addresses are shown
// as a hint only. Outputs are toggled/typed via cmd/set; ANY channel can be
// forced via cmd/force (PLC semantics) — a forced channel reports the forced
// value regardless of the source, which is how inputs are driven in sim.
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

function addressHint(decl: ChannelDecl | undefined): string {
  if (decl === undefined) return "";
  const parts: string[] = [];
  for (const [k, v] of Object.entries(decl)) {
    if (k === "kind" || k === "unit" || k === "scale" || k === "offset") continue;
    parts.push(`${k}=${String(v)}`);
  }
  return parts.join(" ");
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
  const names = useMemo(() => Object.keys(decls), [decls]);

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

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="font-mono">{device.id}</span>
          <span className="text-xs font-normal text-muted-foreground">
            {device.model ?? "dio"} · {device.active ?? "off"}
          </span>
          <Badge variant={alive ? "secondary" : "outline"} className="ml-auto">
            {device.active === "off" ? "off" : alive ? "live" : "no state"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {names.length === 0 ? (
          <p className="text-sm text-muted-foreground">no channels declared</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-xs text-muted-foreground">
              <tr className="[&>th]:py-1 [&>th]:text-left [&>th]:font-medium">
                <th>Channel</th>
                <th className="w-10">Kind</th>
                <th className="w-28">Value</th>
                <th>Control</th>
                <th className="w-8" title="Force (override reported value)" />
              </tr>
            </thead>
            <tbody>
              {names.map((name) => {
                const decl = decls[name];
                const cv = state?.channels[name];
                const isOutput = decl.kind === "do" || decl.kind === "ao";
                const isDigital = decl.kind === "di" || decl.kind === "do";
                const forced = cv?.forced === true;
                const on = cv !== undefined && cv.value === true;
                const controlsOn = canCommand && alive;
                return (
                  <tr
                    key={name}
                    className={cn(
                      "border-t border-border/60 [&>td]:py-1 [&>td]:align-middle",
                      forced && "bg-amber-500/10",
                    )}
                    title={addressHint(decl)}
                  >
                    <td className="font-mono">{name}</td>
                    <td>
                      <span className="text-xs text-muted-foreground">{KIND_LABEL[decl.kind]}</span>
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
                        {formatValue(cv, decl.unit)}
                        {forced && <span className="text-[10px] uppercase">forced</span>}
                      </span>
                    </td>
                    <td>
                      {isDigital ? (
                        <div className="flex gap-1">
                          <Button
                            variant="outline"
                            size="sm"
                            className="cmd h-7 px-2"
                            disabled={!controlsOn || (isOutput && forced)}
                            onClick={() =>
                              void (isOutput ? setOutput(name, !on) : force(name, !on))
                            }
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
                        </div>
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
                          <Button
                            type="submit"
                            variant="outline"
                            size="sm"
                            className="cmd h-7 px-2"
                            disabled={!controlsOn}
                          >
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
                        <span className="inline-flex h-7 w-7 items-center justify-center text-muted-foreground/40" title="not forced">
                          <LockOpen className="size-3.5" />
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
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
