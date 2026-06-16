// Tasks page (gui-design-spec §10, task_runner statechart layer): discover the
// running flows via `task/*/alive` liveliness, select one, Start/Abort it,
// and watch its FSM live. The page is a pure bus citizen — start/abort are
// `cmd/start`/`cmd/abort` queryables; the FSM view renders ONLY the published
// `state`/`result` topics (no optimistic update — a rejected start or a real
// transition is always truthful, mirroring the IoPage rule).
//
// `configuration` carries multiple active state ids while the two parallel
// regions (inspect + conveyor) run, so both regions are visible at once.
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
import { cn } from "@/lib/utils";
import { subscribeLatest, watchTaskFlows, type Unsubscribe } from "../lib/bus";
import { startTask, abortTask } from "../lib/actions";
import { taskResult, taskState } from "../lib/config";
import type { TaskResult, TaskState } from "../lib/messages";

interface TasksPageProps {
  session: Session | null;
  realm: string;
  wsConnected: boolean;
  commandsEnabled: boolean;
}

export default function TasksPage({
  session,
  realm,
  wsConnected,
  commandsEnabled,
}: TasksPageProps) {
  const [flows, setFlows] = useState<string[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [state, setState] = useState<TaskState | null>(null);
  const [result, setResult] = useState<TaskResult | null>(null);
  const [cmdError, setCmdError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  // Discover running flows for this realm via liveliness.
  useEffect(() => {
    if (session === null) return;
    let unsub: Unsubscribe | null = null;
    let disposed = false;
    void (async () => {
      const u = await watchTaskFlows(session, realm, setFlows);
      if (disposed) u();
      else unsub = u;
    })();
    return () => {
      disposed = true;
      unsub?.();
      setFlows([]);
    };
  }, [session, realm]);

  // Auto-select the first flow once discovered (and keep selection valid).
  useEffect(() => {
    if (selected !== null && flows.includes(selected)) return;
    setSelected(flows[0] ?? null);
  }, [flows, selected]);

  // Subscribe to the selected flow's state + result.
  useEffect(() => {
    setState(null);
    setResult(null);
    setCmdError(null);
    if (session === null || selected === null) return;
    const unsubs: Unsubscribe[] = [];
    let disposed = false;
    void (async () => {
      const all = await Promise.all([
        subscribeLatest(
          session,
          taskState(realm, selected),
          (msg) => setState(msg as TaskState),
          8,
        ),
        subscribeLatest(
          session,
          taskResult(realm, selected),
          (msg) => setResult(msg as TaskResult),
          4,
        ),
      ]);
      if (disposed) for (const u of all) u();
      else unsubs.push(...all);
    })();
    return () => {
      disposed = true;
      for (const u of unsubs) u();
    };
  }, [session, realm, selected]);

  const running = state !== null && !state.terminated;
  const startEnabled =
    wsConnected && commandsEnabled && selected !== null && !running && !pending;

  const onStart = async () => {
    if (session === null || selected === null) return;
    setCmdError(null);
    setPending(true);
    setResult(null);
    try {
      const reply = await startTask(session, realm, selected);
      if (!reply.ok) setCmdError(reply.error ?? "start rejected");
    } catch (e) {
      setCmdError(String(e));
    } finally {
      setPending(false);
    }
  };

  const onAbort = async () => {
    if (session === null || selected === null) return;
    setCmdError(null);
    try {
      await abortTask(session, realm, selected);
    } catch (e) {
      setCmdError(String(e));
    }
  };

  const summary = result?.summary ?? state?.context?.summary ?? null;

  return (
    <div className="grid h-full min-h-0 grid-cols-[220px_1fr] gap-2 overflow-hidden p-2">
      {/* flow list */}
      <Card size="sm" className="min-h-0 overflow-y-auto">
        <CardHeader>
          <CardTitle>Flows</CardTitle>
        </CardHeader>
        <CardContent>
          {flows.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              no task_runner running
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              {flows.map((m) => (
                <Button
                  key={m}
                  variant="outline"
                  size="sm"
                  className={cn(
                    "cmd justify-start font-mono",
                    m === selected && "border-ok bg-ok/20 text-ok",
                  )}
                  onClick={() => setSelected(m)}
                  title={m}
                >
                  {m}
                </Button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* selected flow */}
      <div className="grid min-h-0 grid-rows-[auto_1fr] gap-2 overflow-hidden">
        <Card size="sm">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="font-mono">{selected ?? "—"}</CardTitle>
            <div className="flex items-center gap-2">
              <RunBadge state={state} />
              <Button
                size="sm"
                className="cmd"
                disabled={!startEnabled}
                onClick={() => void onStart()}
                title="Run cmd/start"
              >
                {pending ? "Starting…" : "Start"}
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="cmd"
                disabled={!wsConnected || selected === null || !running}
                onClick={() => void onAbort()}
                title="Run cmd/abort"
              >
                Abort
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {cmdError !== null && (
              <p className="text-sm text-destructive">{cmdError}</p>
            )}
          </CardContent>
        </Card>

        <div className="grid min-h-0 grid-cols-2 gap-2 overflow-hidden">
          {/* live FSM */}
          <Card size="sm" className="min-h-0 overflow-y-auto">
            <CardHeader>
              <CardTitle>State machine</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {state === null ? (
                <p className="text-sm text-muted-foreground">
                  no state — start a run
                </p>
              ) : (
                <>
                  <div>
                    <p className="mb-1 text-xs text-muted-foreground">
                      active configuration
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {state.configuration.map((id) => (
                        <Badge
                          key={id}
                          variant="outline"
                          className="border-ok bg-ok/20 font-mono text-ok"
                        >
                          {id}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="mb-1 text-xs text-muted-foreground">
                      transitions
                    </p>
                    <div className="flex flex-col gap-0.5 font-mono text-xs tabular-nums">
                      {state.history.length === 0 ? (
                        <span className="text-muted-foreground">—</span>
                      ) : (
                        state.history
                          .slice(-12)
                          .map((h, i) => (
                            <span key={i}>
                              <span className="text-muted-foreground">
                                {h.source ?? "∅"}
                              </span>
                              {" → "}
                              <span>{h.target ?? "∅"}</span>{" "}
                              <span className="text-muted-foreground">
                                ({h.event})
                              </span>
                            </span>
                          ))
                      )}
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          {/* result / summary */}
          <Card size="sm" className="min-h-0 overflow-y-auto">
            <CardHeader>
              <CardTitle>Result</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2 text-sm">
              {result !== null && (
                <div className="flex items-center gap-2">
                  <Badge
                    variant="outline"
                    className={cn(
                      "font-mono",
                      result.ok
                        ? "border-ok bg-ok/20 text-ok"
                        : "border-destructive bg-destructive/20 text-destructive",
                    )}
                  >
                    {result.ok ? "ok" : "failed"}
                  </Badge>
                  {result.error !== null && (
                    <span className="font-mono text-xs text-destructive">
                      {result.error}
                    </span>
                  )}
                </div>
              )}
              {summary !== null ? (
                <div className="flex flex-col gap-2 font-mono text-xs">
                  <div>
                    <span className="text-muted-foreground">codes</span>{" "}
                    {summary.codes.length === 0
                      ? "—"
                      : summary.codes.join(", ")}
                  </div>
                  {summary.conveyor !== null && (
                    <div>
                      <span className="text-muted-foreground">conveyor</span>{" "}
                      {summary.conveyor.tripped_by} (
                      {summary.conveyor.elapsed_s.toFixed(2)}s)
                    </div>
                  )}
                  {summary.by_pose !== undefined &&
                    summary.by_pose.length > 0 && (
                      <div className="flex flex-col gap-0.5">
                        <span className="text-muted-foreground">by pose</span>
                        {summary.by_pose.map((p) => (
                          <span key={p.pose}>
                            {p.pose}:{" "}
                            {p.detections.map((d) => d.text).join(", ") || "—"}
                          </span>
                        ))}
                      </div>
                    )}
                </div>
              ) : (
                <p className="text-muted-foreground">no result yet</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function RunBadge({ state }: { state: TaskState | null }) {
  let label = "idle";
  let cls = "border-border text-muted-foreground";
  if (state !== null) {
    if (!state.terminated) {
      label = "running";
      cls = "border-ok bg-ok/20 text-ok";
    } else {
      label = "terminated";
      cls = "border-border text-muted-foreground";
    }
  }
  return (
    <Badge variant="outline" className={cn("font-mono", cls)}>
      {label}
    </Badge>
  );
}
