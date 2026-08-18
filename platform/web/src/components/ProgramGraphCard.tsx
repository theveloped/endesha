// "Program graph" card: the loaded (or a chosen) program's state machine with
// the live overlay, node positions persisted in the config store. Used in the
// Programs tool and, compact, on the HMI.
import { useCallback, useMemo, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { programEvent } from "../lib/actions";
import type { CatalogEntry, ProgramState, TransitionEvent } from "../lib/messages";
import { useProgramLayout } from "../runtime/useProgramLayout";
import { ProgramGraph } from "./ProgramGraph";

export function ProgramGraphCard({
  session,
  realm,
  entries,
  state,
  transitions,
  compact = false,
  height = 320,
  onError,
}: {
  session: Session | null;
  realm: string;
  entries: CatalogEntry[];
  state: ProgramState | null;
  transitions: TransitionEvent[];
  compact?: boolean;
  height?: number;
  onError?: (message: string | null) => void;
}) {
  const [picked, setPicked] = useState<string | null>(null);
  const loadedName = state?.program ?? null;
  const name = loadedName ?? picked ?? entries.find((e) => e.graph !== undefined)?.name ?? null;
  const entry = useMemo(() => entries.find((e) => e.name === name) ?? null, [entries, name]);
  const { layout, save } = useProgramLayout(session, entry?.name ?? null);
  const graph = entry?.graph;
  const live = loadedName !== null && loadedName === entry?.name;

  const sendEvent = useCallback(
    (event: string) => {
      if (session === null) return;
      void programEvent(session, realm, event)
        .then((ack) => onError?.(ack.ok ? null : `event ${event}: ${ack.error ?? "failed"}`))
        .catch((e) => onError?.(`event ${event}: ${String(e)}`));
    },
    [session, realm, onError],
  );

  if (entries.length === 0) return null;
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span>Program graph</span>
          {live ? (
            <Badge variant="secondary">live</Badge>
          ) : (
            <select
              className="h-6 rounded border border-border bg-background px-1 font-mono text-xs"
              value={entry?.name ?? ""}
              onChange={(ev) => setPicked(ev.target.value)}
              title="No program loaded: pick one to view its design"
            >
              {entries
                .filter((e) => e.graph !== undefined)
                .map((e) => (
                  <option key={e.name} value={e.name}>
                    {e.name}
                  </option>
                ))}
            </select>
          )}
          {!compact && (
            <span className="ml-auto text-xs font-normal text-muted-foreground">
              {live ? "active state, armed transitions and the last taken edge follow the runner" : "design view — load it to see it run"}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {graph === undefined || graph.states.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {entry?.error ? `no graph: ${entry.error.split("\n").pop()}` : "no graph exported for this program"}
          </p>
        ) : (
          <div style={{ height }} className="overflow-hidden rounded-md border border-border">
            <ProgramGraph
              graph={graph}
              live={live ? { state, transitions } : undefined}
              layout={layout}
              compact={compact}
              onLayoutChange={compact ? undefined : (l) => void save(l).catch((e) => onError?.(`layout: ${String(e)}`))}
              onSendEvent={live ? sendEvent : undefined}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
