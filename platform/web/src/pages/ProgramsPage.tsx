// Programs tool (program-layer RFC §7.2): the cell's program unit — catalog,
// load (bindings + params), PackML command bar, live unit/program state,
// external events, transition log. Program commands do NOT need the operator
// lease: the running program holds it; the operator commands the unit.
import { useEffect, useMemo, useState, type RefObject } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { Badge } from "../catalyst/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { ProgramGraphCard } from "../components/ProgramGraphCard";
import { configDelete, configSet, programCommand, programEvent, programLoad } from "../lib/actions";
import { subscribeConfigList, type Unsubscribe } from "../lib/bus";
import { configProgramPose, configProgramPosesGlob, type UnitCommand } from "../lib/config";
import type {
  CatalogEntry,
  DeviceEntry,
  JointState,
  PoseDef,
  ProgramLogLine,
  ProgramState,
  TransitionEvent,
  WaitingFor,
} from "../lib/messages";
import { unitAccepts, unitLabel, unitTone } from "../lib/unit";
import type { ProgramView } from "../runtime/useProgram";

interface ProgramsPageProps {
  session: Session | null;
  realm: string;
  devices: DeviceEntry[];
  program: ProgramView;
  wsConnected: boolean;
  jointsRef: RefObject<JointState | null>;
  onEdit: (programName: string | null) => void;
}

const COMMAND_LABEL: Record<UnitCommand, string> = {
  start: "Start",
  hold: "Hold",
  unhold: "Unhold",
  suspend: "Suspend",
  unsuspend: "Unsuspend",
  stop: "Stop",
  abort: "Abort",
  clear: "Clear",
  reset: "Reset",
  unload: "Unload",
};

const PRIMARY: UnitCommand[] = ["start", "hold", "unhold", "stop", "reset", "clear"];
const SECONDARY: UnitCommand[] = ["suspend", "unsuspend", "abort", "unload"];

function formatTime(t: unknown): string {
  const ns = typeof t === "bigint" ? Number(t / 1000000n) : Number(t) / 1e6;
  return new Date(ns).toLocaleTimeString(undefined, { hour12: false });
}

export function UnitBadge({ state, alive }: { state: ProgramState | null; alive: boolean }) {
  const unit = alive ? (state?.unit ?? null) : null;
  return (
    <Badge color={unitTone(unit)} className="font-mono">
      {unitLabel(unit)}
    </Badge>
  );
}

export function CommandBar({
  session,
  realm,
  state,
  alive,
  commands,
  onError,
  size = "sm",
}: {
  session: Session | null;
  realm: string;
  state: ProgramState | null;
  alive: boolean;
  commands: UnitCommand[];
  onError: (message: string | null) => void;
  size?: "sm" | "lg";
}) {
  const [busy, setBusy] = useState<UnitCommand | null>(null);
  const unit = alive ? (state?.unit ?? null) : null;
  const send = async (command: UnitCommand) => {
    if (session === null) return;
    setBusy(command);
    onError(null);
    try {
      const ack = await programCommand(session, realm, command);
      if (!ack.ok) onError(`${command}: ${ack.error ?? "failed"}`);
    } catch (e) {
      onError(`${command}: ${String(e)}`);
    } finally {
      setBusy(null);
    }
  };
  return (
    <div className="flex flex-wrap gap-1">
      {commands.map((command) => {
        const enabled = unitAccepts(unit, command) && (command !== "start" || state?.program !== null);
        const danger = command === "abort" || command === "stop";
        return (
          <Button
            key={command}
            variant={danger ? "destructive" : command === "start" || command === "unhold" ? "default" : "outline"}
            size={size === "lg" ? "lg" : "sm"}
            className={cn("cmd", size === "lg" && "h-14 min-w-28 text-base")}
            disabled={!enabled || busy !== null || session === null}
            onClick={() => void send(command)}
            title={enabled ? `${COMMAND_LABEL[command]} the unit` : `${COMMAND_LABEL[command]} not accepted in ${unit ?? "no runner"}`}
          >
            {COMMAND_LABEL[command]}
          </Button>
        );
      })}
    </div>
  );
}

function CatalogCard({
  session,
  realm,
  entries,
  devices,
  state,
  onError,
  onRefresh,
  onEdit,
}: {
  session: Session | null;
  realm: string;
  entries: CatalogEntry[];
  devices: DeviceEntry[];
  state: ProgramState | null;
  onError: (message: string | null) => void;
  onRefresh: () => void;
  onEdit: (programName: string | null) => void;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [bindings, setBindings] = useState<Record<string, string>>({});
  const [paramDrafts, setParamDrafts] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const entry = entries.find((e) => e.name === selected) ?? null;
  const canLoad = state !== null && (state.unit === "idle" || state.unit === "stopped");

  useEffect(() => {
    // Default bindings: sole device of the role's contract; params: defaults.
    if (entry === null) return;
    const next: Record<string, string> = {};
    for (const [role, contract] of Object.entries(entry.roles)) {
      const candidates = devices.filter((d) => d.contract === contract);
      if (candidates.length === 1) next[role] = candidates[0].id;
    }
    setBindings(next);
    setParamDrafts(Object.fromEntries(Object.entries(entry.params).map(([k, v]) => [k, JSON.stringify(v)])));
  }, [entry, devices]);

  const load = async () => {
    if (session === null || entry === null) return;
    setBusy(true);
    onError(null);
    try {
      const params: Record<string, unknown> = {};
      for (const [k, raw] of Object.entries(paramDrafts)) {
        const defaultRaw = JSON.stringify(entry.params[k]);
        if (raw === defaultRaw) continue;
        try {
          params[k] = JSON.parse(raw);
        } catch {
          params[k] = raw;
        }
      }
      const ack = await programLoad(session, realm, entry.name, bindings, params);
      if (!ack.ok) onError(`load: ${ack.error ?? "failed"}`);
    } catch (e) {
      onError(`load: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Programs
          <span className="text-xs font-normal text-muted-foreground">deploy/programs</span>
          <Button variant="outline" size="sm" className="ml-auto h-7 px-2 text-xs" onClick={() => onEdit(null)} title="Open the program editor">
            new / edit
          </Button>
          <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={onRefresh}>
            rescan
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">No programs found.</p>
        ) : (
          <ul className="divide-y divide-border/60 rounded-md border border-border/60">
            {entries.map((e) => (
              <li key={e.name}>
                <button
                  type="button"
                  className={cn(
                    "flex w-full items-start gap-2 px-2 py-1.5 text-left text-sm hover:bg-muted/60",
                    selected === e.name && "bg-muted",
                  )}
                  onClick={() => setSelected(e.name)}
                >
                  <span className="font-mono">{e.name}</span>
                  {e.error !== null ? (
                    <Badge color="red">broken</Badge>
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      {Object.entries(e.roles).map(([r, c]) => `${r}:${c}`).join(" ")}
                    </span>
                  )}
                  {state?.program === e.name && <Badge color="blue" className="ml-auto">loaded</Badge>}
                </button>
              </li>
            ))}
          </ul>
        )}
        {entry !== null && (
          <div className="space-y-2 rounded-md border border-border/60 p-2">
            {entry.error !== null ? (
              <>
                <pre className="whitespace-pre-wrap text-xs text-destructive">{entry.error}</pre>
                <Button variant="outline" size="sm" onClick={() => onEdit(entry.name)}>
                  Fix in editor
                </Button>
              </>
            ) : (
              <>
                {entry.doc && <p className="text-xs text-muted-foreground">{entry.doc}</p>}
                {Object.keys(entry.roles).length > 0 && (
                  <div className="space-y-1">
                    <div className="text-xs font-medium text-muted-foreground">Roles</div>
                    {Object.entries(entry.roles).map(([role, contract]) => (
                      <label key={role} className="flex items-center gap-2 text-sm">
                        <span className="w-24 font-mono">{role}</span>
                        <select
                          className="h-7 flex-1 rounded border border-border bg-background px-1 font-mono text-xs"
                          value={bindings[role] ?? ""}
                          onChange={(ev) => setBindings((b) => ({ ...b, [role]: ev.target.value }))}
                        >
                          <option value="">— pick a {contract} —</option>
                          {devices.filter((d) => d.contract === contract).map((d) => (
                            <option key={d.id} value={d.id}>{d.id}</option>
                          ))}
                        </select>
                      </label>
                    ))}
                  </div>
                )}
                {Object.keys(entry.params).length > 0 && (
                  <div className="space-y-1">
                    <div className="text-xs font-medium text-muted-foreground">Params (JSON)</div>
                    {Object.keys(entry.params).map((k) => (
                      <label key={k} className="flex items-center gap-2 text-sm">
                        <span className="w-24 font-mono">{k}</span>
                        <Input
                          className="h-7 flex-1 font-mono text-xs"
                          value={paramDrafts[k] ?? ""}
                          onChange={(ev) => setParamDrafts((d) => ({ ...d, [k]: ev.target.value }))}
                        />
                      </label>
                    ))}
                  </div>
                )}
                <div className="flex gap-1">
                  <Button
                    size="sm"
                    className="cmd"
                    disabled={!canLoad || busy || session === null}
                    onClick={() => void load()}
                    title={canLoad ? "Load into the unit" : "Unit must be Idle or Stopped to load"}
                  >
                    Load {entry.name}
                  </Button>
                  <Button variant="outline" size="sm" onClick={() => onEdit(entry.name)} title="Open in the editor">
                    Edit
                  </Button>
                </div>
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function describeWait(w: WaitingFor): string {
  switch (w.kind) {
    case "channel":
      return `${w.role}.${w.channel} ${w.edge} → ${w.event}${w.target ? ` (→ ${w.target})` : ""}`;
    case "timer":
      return `after ${w.seconds}s in ${w.state} → ${w.event}${w.target ? ` (→ ${w.target})` : ""}`;
    default:
      return `event "${w.event}"${w.target ? ` (→ ${w.target})` : ""} — from an action's emit() or "Send event"`;
  }
}

function WaitingForCard({ state, alive }: { state: ProgramState | null; alive: boolean }) {
  if (!alive || state === null || state.unit !== "execute") return null;
  const waits = state.waiting_for ?? [];
  const running = state.actions.length > 0;
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {running ? "Running" : "Waiting for"}
          <span className="text-xs font-normal text-muted-foreground">
            {running
              ? `action${state.actions.length > 1 ? "s" : ""} ${state.actions.join(", ")} in progress`
              : "the program is idle in its current state until one of these happens"}
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {waits.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No outgoing transition from {state.program_states.join(", ") || "the current state"} — is it final?
          </p>
        ) : (
          <ul className="space-y-0.5 font-mono text-xs">
            {waits.map((w, i) => (
              <li key={i} className="flex items-start gap-2">
                <Badge color={w.kind === "channel" ? "emerald" : w.kind === "timer" ? "sky" : "zinc"} className="mt-0.5">
                  {w.kind}
                </Badge>
                <span>{describeWait(w)}</span>
              </li>
            ))}
          </ul>
        )}
        {!running && waits.some((w) => w.kind === "channel") && (
          <p className="mt-2 text-xs text-muted-foreground">
            In sim, drive an input from the IO tool (force) or <span className="font-mono">wfctl dio-force &lt;channel&gt; on</span>.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function LogCard({ log }: { log: ProgramLogLine[] }) {
  const items = useMemo(() => [...log].reverse().slice(0, 80), [log]);
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Log</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">nothing yet — programs write here with self.log(...)</p>
        ) : (
          <ul className="max-h-56 space-y-0.5 overflow-y-auto font-mono text-xs">
            {items.map((l, i) => (
              <li key={`${String(l.t)}-${i}`} className="flex gap-2">
                <span className="text-muted-foreground">{formatTime(l.t)}</span>
                <span className={cn("w-14 shrink-0", l.source === "runner" ? "text-sky-600 dark:text-sky-400" : "text-emerald-600 dark:text-emerald-400")}>
                  {l.source}
                </span>
                <span className={cn(l.level === "error" && "text-destructive", l.level === "warning" && "text-amber-600 dark:text-amber-400")}>
                  {l.message}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function StateCard({ state, alive }: { state: ProgramState | null; alive: boolean }) {
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Unit
          <UnitBadge state={state} alive={alive} />
          {!alive && <span className="text-xs font-normal text-destructive">program runner not alive</span>}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-[7rem_1fr] gap-x-2 gap-y-1 text-sm">
          <dt className="text-muted-foreground">program</dt>
          <dd className="font-mono">{state?.program ?? "—"}</dd>
          <dt className="text-muted-foreground">program states</dt>
          <dd className="font-mono">{state && state.program_states.length ? state.program_states.join(", ") : "—"}</dd>
          <dt className="text-muted-foreground">running actions</dt>
          <dd className="font-mono">{state && state.actions.length ? state.actions.join(", ") : "—"}</dd>
          <dt className="text-muted-foreground">bindings</dt>
          <dd className="font-mono text-xs">
            {state && Object.keys(state.bindings).length
              ? Object.entries(state.bindings).map(([r, id]) => `${r}→${id}`).join("  ")
              : "—"}
          </dd>
          <dt className="text-muted-foreground">params</dt>
          <dd className="font-mono text-xs">{state && Object.keys(state.params).length ? JSON.stringify(state.params) : "—"}</dd>
          <dt className="text-muted-foreground">cycle</dt>
          <dd className="font-mono">{state?.cycle ?? "—"}</dd>
          {state?.reason && (
            <>
              <dt className="text-muted-foreground">reason</dt>
              <dd className="font-mono text-xs text-destructive">{state.reason}</dd>
            </>
          )}
        </dl>
      </CardContent>
    </Card>
  );
}

function EventCard({
  session,
  realm,
  state,
  onError,
}: {
  session: Session | null;
  realm: string;
  state: ProgramState | null;
  onError: (message: string | null) => void;
}) {
  const [event, setEvent] = useState("");
  const enabled = session !== null && state?.unit === "execute" && event.trim() !== "";
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Send event</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          className="flex items-center gap-1"
          onSubmit={(ev) => {
            ev.preventDefault();
            if (!enabled || session === null) return;
            void programEvent(session, realm, event.trim())
              .then((ack) => onError(ack.ok ? null : `event: ${ack.error ?? "failed"}`))
              .catch((e) => onError(`event: ${String(e)}`));
          }}
        >
          <Input
            className="h-7 flex-1 font-mono text-xs"
            placeholder="event name (only while executing)"
            value={event}
            onChange={(ev) => setEvent(ev.target.value)}
          />
          <Button type="submit" variant="outline" size="sm" className="cmd h-7" disabled={!enabled}>
            send
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function ProgramPosesCard({
  session,
  programName,
  jointsRef,
  onError,
}: {
  session: Session | null;
  programName: string;
  jointsRef: RefObject<JointState | null>;
  onError: (message: string | null) => void;
}) {
  const [poses, setPoses] = useState<{ name: string; value: PoseDef }[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const glob = configProgramPosesGlob(programName);

  useEffect(() => {
    setPoses([]);
    if (session === null) return;
    let disposed = false;
    let unsub: Unsubscribe | null = null;
    void subscribeConfigList(session, glob, `config/programs/${programName}/poses/`, (items) =>
      setPoses(items.map((i) => ({ name: i.name, value: i.value as PoseDef })).sort((a, b) => a.name.localeCompare(b.name))),
    ).then((u) => {
      if (disposed) u();
      else unsub = u;
    });
    return () => {
      disposed = true;
      unsub?.();
    };
  }, [session, glob, programName]);

  const teach = async (name: string) => {
    if (session === null) return;
    const q = jointsRef.current?.q;
    if (q === undefined) {
      onError("teach: no joint state");
      return;
    }
    setBusy(true);
    onError(null);
    try {
      const reply = await configSet(session, configProgramPose(programName, name), { q: [...q] });
      if (!reply.ok) onError(`teach ${name}: ${reply.error ?? "failed"}`);
      else setDraft("");
    } catch (e) {
      onError(`teach ${name}: ${String(e)}`);
    } finally {
      setBusy(false);
    }
  };
  const remove = async (name: string) => {
    if (session === null) return;
    try {
      const reply = await configDelete(session, configProgramPose(programName, name));
      if (!reply.ok) onError(`delete ${name}: ${reply.error ?? "failed"}`);
    } catch (e) {
      onError(`delete ${name}: ${String(e)}`);
    }
  };
  const valid = /^[a-z][a-z0-9_]*$/.test(draft);

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Program poses
          <span className="text-xs font-normal text-muted-foreground">
            config/programs/{programName}/poses — resolved before cell poses
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {poses.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No program-scoped poses. A pose taught here overrides a cell pose of the same name for
            this program only, so the program travels between cells.
          </p>
        ) : (
          <ul className="divide-y divide-border/60 rounded-md border border-border/60 font-mono text-xs">
            {poses.map((p) => (
              <li key={p.name} className="flex items-center gap-2 px-2 py-1">
                <span>{p.name}</span>
                <span className="text-muted-foreground">
                  {p.value.q.map((v) => ((v * 180) / Math.PI).toFixed(1)).join(", ")}°
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-auto h-6 px-2 text-xs"
                  disabled={session === null || busy}
                  onClick={() => void teach(p.name)}
                  title="Re-teach from the current joints"
                >
                  re-teach
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-6 px-2 text-xs text-destructive"
                  disabled={session === null}
                  onClick={() => void remove(p.name)}
                >
                  delete
                </Button>
              </li>
            ))}
          </ul>
        )}
        <form
          className="flex items-center gap-1"
          onSubmit={(ev) => {
            ev.preventDefault();
            if (valid) void teach(draft);
          }}
        >
          <Input
            className="h-7 flex-1 font-mono text-xs"
            placeholder="pose name (a-z, 0-9, _)"
            value={draft}
            onChange={(ev) => setDraft(ev.target.value)}
          />
          <Button
            type="submit"
            variant="outline"
            size="sm"
            className="cmd h-7"
            disabled={!valid || busy || session === null}
            title="Store the arm's current joints under this name for this program"
          >
            teach current
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function TransitionsCard({ transitions }: { transitions: TransitionEvent[] }) {
  const items = useMemo(() => [...transitions].reverse().slice(0, 60), [transitions]);
  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Transitions</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <p className="text-sm text-muted-foreground">nothing yet</p>
        ) : (
          <ul className="max-h-64 space-y-0.5 overflow-y-auto font-mono text-xs">
            {items.map((t, i) => (
              <li key={`${String(t.t)}-${i}`} className="flex gap-2">
                <span className="text-muted-foreground">{formatTime(t.t)}</span>
                <span className={cn("w-14", t.scope === "unit" ? "text-sky-600 dark:text-sky-400" : "text-emerald-600 dark:text-emerald-400")}>
                  {t.scope}
                </span>
                <span>
                  {t.source ?? "∅"} → {t.target}
                  {t.event && <span className="text-muted-foreground"> on {t.event}</span>}
                  {t.detail && <span className="text-destructive"> ({t.detail})</span>}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

export default function ProgramsPage({ session, realm, devices, program, wsConnected, jointsRef, onEdit }: ProgramsPageProps) {
  const [error, setError] = useState<string | null>(null);
  const alive = wsConnected && program.alive;
  return (
    <div className="h-full space-y-2 overflow-y-auto p-2">
      <Card size="sm">
        <CardContent className="space-y-2">
          <div className="flex items-center gap-2">
            <UnitBadge state={program.state} alive={alive} />
            <span className="font-mono text-sm">{program.state?.program ?? "no program loaded"}</span>
          </div>
          <CommandBar session={session} realm={realm} state={program.state} alive={alive} commands={PRIMARY} onError={setError} />
          <CommandBar session={session} realm={realm} state={program.state} alive={alive} commands={SECONDARY} onError={setError} />
          {error !== null && <p className="text-sm text-destructive">{error}</p>}
        </CardContent>
      </Card>
      <ProgramGraphCard
        session={session}
        realm={realm}
        entries={program.catalog?.programs ?? []}
        state={alive ? program.state : null}
        transitions={program.transitions}
        onError={setError}
      />
      <WaitingForCard state={program.state} alive={alive} />
      <StateCard state={program.state} alive={alive} />
      <LogCard log={program.log} />
      <CatalogCard
        session={session}
        realm={realm}
        entries={program.catalog?.programs ?? []}
        devices={devices}
        state={program.state}
        onError={setError}
        onRefresh={program.refreshCatalog}
        onEdit={onEdit}
      />
      {program.state?.program && (
        <ProgramPosesCard session={session} programName={program.state.program} jointsRef={jointsRef} onError={setError} />
      )}
      <EventCard session={session} realm={realm} state={program.state} onError={setError} />
      <TransitionsCard transitions={program.transitions} />
    </div>
  );
}
