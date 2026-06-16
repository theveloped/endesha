// Flows page (design §8 "flow selection"): the supervisor is the sole flow
// interpreter — it publishes a `flows/catalog` of selectable flows with their
// RESOLVED role bindings (arm→r1, cam→cam0) and brings each online/offline on
// demand. This page reads the catalog (latest-wins) and clicks Bring online /
// Take offline (flows/cmd/start|stop queryables). It does NOT run a flow:
// bring a flow online here, then run it on the Tasks page. No optimistic
// update — a row flips on the next catalog publish (mirrors the Tasks rule).
import { useEffect, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { query, subscribeLatest, watchAlive, type Unsubscribe } from "../lib/bus";
import { startFlow, stopFlow } from "../lib/actions";
import { flowsCatalog, supervisorAlive } from "../lib/config";
import type { FlowCatalogEntry, FlowsCatalog } from "../lib/messages";

interface FlowsPageProps {
  session: Session | null;
  realm: string;
  wsConnected: boolean;
  commandsEnabled: boolean;
}

export default function FlowsPage({
  session,
  realm,
  wsConnected,
  commandsEnabled,
}: FlowsPageProps) {
  const [flows, setFlows] = useState<FlowCatalogEntry[]>([]);
  const [supUp, setSupUp] = useState(false);
  const [cmdError, setCmdError] = useState<string | null>(null);
  const [pending, setPending] = useState<string | null>(null);

  useEffect(() => {
    setFlows([]);
    setSupUp(false);
    setCmdError(null);
    if (session === null) return;
    const unsubs: Unsubscribe[] = [];
    let disposed = false;
    void (async () => {
      // The catalog is latest-wins + queryable: query once for the current
      // state (a browser that connects after the supervisor's last publish
      // would otherwise see nothing until the next change), then subscribe for
      // live updates.
      const all = await Promise.all([
        subscribeLatest(
          session,
          flowsCatalog(realm),
          (msg) => setFlows((msg as FlowsCatalog).flows ?? []),
          4,
        ),
        watchAlive(session, supervisorAlive(realm), setSupUp),
      ]);
      if (disposed) {
        for (const u of all) u();
        return;
      }
      unsubs.push(...all);
      const current = await query(session, flowsCatalog(realm), {});
      if (!disposed && current !== null) {
        setFlows((current as FlowsCatalog).flows ?? []);
      }
    })();
    return () => {
      disposed = true;
      for (const u of unsubs) u();
    };
  }, [session, realm]);

  const act = async (
    fn: typeof startFlow | typeof stopFlow,
    flow: string,
  ) => {
    if (session === null) return;
    setCmdError(null);
    setPending(flow);
    try {
      const reply = await fn(session, realm, flow);
      if (!reply.ok) setCmdError(reply.error ?? "command rejected");
    } catch (e) {
      setCmdError(String(e));
    } finally {
      setPending(null);
    }
  };

  const gated = wsConnected && commandsEnabled && supUp;

  return (
    <div className="grid h-full min-h-0 grid-rows-[auto_1fr] gap-2 overflow-hidden p-2">
      <Card size="sm">
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Flows</CardTitle>
          <Badge
            variant="outline"
            className={
              supUp
                ? "border-ok bg-ok/20 text-ok"
                : "border-destructive bg-destructive/20 text-destructive"
            }
          >
            {supUp ? "supervisor up" : "supervisor down"}
          </Badge>
        </CardHeader>
        <CardContent className="flex flex-col gap-1">
          <p className="text-sm text-muted-foreground">
            Bring a flow online here, then run it on the Tasks page.
          </p>
          {cmdError !== null && (
            <p className="text-sm text-destructive">{cmdError}</p>
          )}
        </CardContent>
      </Card>

      <Card size="sm" className="min-h-0 overflow-y-auto">
        <CardContent className="flex flex-col gap-2 pt-3">
          {flows.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {supUp ? "no flows in catalog" : "no supervisor running"}
            </p>
          ) : (
            flows.map((f) => (
              <FlowRow
                key={f.name}
                flow={f}
                gated={gated}
                pending={pending === f.name}
                onStart={() => void act(startFlow, f.name)}
                onStop={() => void act(stopFlow, f.name)}
              />
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function FlowRow({
  flow,
  gated,
  pending,
  onStart,
  onStop,
}: {
  flow: FlowCatalogEntry;
  gated: boolean;
  pending: boolean;
  onStart: () => void;
  onStop: () => void;
}) {
  const bindings = Object.entries(flow.roles)
    .map(([role, b]) => `${role}→${b.resource_id}`)
    .join(", ");
  return (
    <div className="flex items-center justify-between gap-3 rounded border border-border p-2">
      <div className="flex min-w-0 flex-col gap-0.5">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm">{flow.name}</span>
          <Badge
            variant="outline"
            className={
              flow.online
                ? "border-ok bg-ok/20 text-ok"
                : "border-border text-muted-foreground"
            }
          >
            {flow.online ? "online" : "offline"}
          </Badge>
        </div>
        <span className="font-mono text-xs text-muted-foreground">
          {bindings || "—"}
          {flow.pipeline ? ` · ${flow.pipeline}` : ""}
        </span>
        {flow.error !== null && (
          <span className="text-xs text-destructive">{flow.error}</span>
        )}
      </div>
      <Button
        size="sm"
        variant={flow.online ? "outline" : "default"}
        className="cmd shrink-0"
        disabled={!gated || pending || flow.error !== null}
        onClick={flow.online ? onStop : onStart}
        title={flow.online ? "flows/cmd/stop" : "flows/cmd/start"}
      >
        {pending
          ? "…"
          : flow.online
            ? "Take offline"
            : "Bring online"}
      </Button>
    </div>
  );
}
