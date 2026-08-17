// One parts washer (`washer` contract): live phase / door / fault, the four
// handshake actions (open door, close door, start wash, reset) with cancel
// (stops a travelling door), and the machine's wash program as an editable
// recipe. Actions and recipe writes are gated by the cell control lease; the
// card renders the status stream, never the click.
import { useCallback, useEffect, useMemo, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import {
  washerAction,
  washerCancel,
  washerGetRecipe,
  washerSetRecipe,
  washerStopDoor,
  type WasherAction,
} from "../lib/actions";
import { subscribeLatest, type Unsubscribe } from "../lib/bus";
import { washerState } from "../lib/config";
import type { Recipe, RecipeSchema, RecipeStep, WasherStatus } from "../lib/messages";

const PHASE_LABEL: Record<string, string> = {
  initializing: "Initializing",
  ready_to_load: "Ready to load",
  door_open: "Door open",
  door_moving: "Door moving",
  washing: "Washing",
  ready_to_unload: "Ready to unload",
  fault: "FAULT",
};

const PHASE_CLASS: Record<string, string> = {
  ready_to_load: "border-ok bg-ok/15 text-ok",
  ready_to_unload: "border-ok bg-ok/15 text-ok",
  door_open: "border-sky-500 bg-sky-500/15 text-sky-700 dark:text-sky-300",
  door_moving: "border-amber-500 bg-amber-500/15 text-amber-700 dark:text-amber-300",
  washing: "border-sky-500 bg-sky-500/15 text-sky-700 dark:text-sky-300",
  fault: "border-destructive bg-destructive/15 text-destructive",
  initializing: "border-border text-muted-foreground",
};

/** Which actions make sense in which phase (mirrors WasherCore's accept). */
const ACTIONS: { name: WasherAction; label: string; phases: string[] | null }[] = [
  { name: "open_door", label: "Open door", phases: ["ready_to_load", "ready_to_unload"] },
  { name: "start_wash", label: "Close & start wash", phases: ["door_open"] },
  { name: "close_door", label: "Close door", phases: ["door_open"] },
  { name: "reset", label: "Reset", phases: null },
];

export function WasherCard({
  session,
  realm,
  rid,
  active,
  clientId,
  canCommand,
  showRecipe = false,
  operator = false,
}: {
  session: Session | null;
  realm: string;
  rid: string;
  active: string | null;
  clientId: string;
  canCommand: boolean;
  /** Show the recipe editor (engineering workspace). */
  showRecipe?: boolean;
  /** Bigger buttons, fewer details (HMI). */
  operator?: boolean;
}) {
  const [status, setStatus] = useState<WasherStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [goal, setGoal] = useState<{ id: string; name: WasherAction } | null>(null);
  const [programNo, setProgramNo] = useState("");

  useEffect(() => {
    if (session === null || active === null || active === "off") return;
    let disposed = false;
    let unsubscribe: Unsubscribe | null = null;
    void (async () => {
      const next = await subscribeLatest(session, washerState(realm, rid), (m) => setStatus(m as WasherStatus), 4);
      if (disposed) next();
      else unsubscribe = next;
    })();
    return () => {
      disposed = true;
      unsubscribe?.();
      setStatus(null);
    };
  }, [session, realm, rid, active]);

  const alive = status !== null;
  const phase = status?.phase ?? "initializing";
  const busy = goal !== null || (status?.sequence ?? null) !== null;

  const run = async (name: WasherAction) => {
    if (session === null) return;
    setError(null);
    const extra: Record<string, unknown> = {};
    if (name === "start_wash" && programNo.trim() !== "") {
      const n = Number(programNo);
      if (!Number.isInteger(n)) {
        setError("program number must be an integer");
        return;
      }
      extra.program = n;
    }
    try {
      const handle = await washerAction(session, realm, rid, clientId, name, extra);
      setGoal({ id: handle.goalId, name });
      const result = await handle.result;
      setGoal(null);
      if (result.state !== "succeeded") setError(`${name}: ${result.state}${result.error ? ` (${result.error})` : ""}`);
    } catch (e) {
      setGoal(null);
      setError(`${name}: ${String(e)}`);
    }
  };

  const cancel = async () => {
    if (session === null) return;
    try {
      if (goal !== null) await washerCancel(session, realm, rid, goal.id);
      else await washerStopDoor(session, realm, rid, clientId);
    } catch (e) {
      setError(`stop: ${String(e)}`);
    }
  };

  const btn = operator ? "cmd h-11 px-5 text-base" : "cmd h-8 px-3";

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <span className="font-mono">{rid}</span>
          <span className="text-xs font-normal text-muted-foreground">washer · {active ?? "off"}</span>
          <Badge variant={alive ? "secondary" : "outline"} className="ml-auto">
            {active === "off" ? "off" : !alive ? "no state" : status?.connected ? "connected" : "disconnected"}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={cn(
              "inline-flex items-center rounded-md border px-2 py-0.5 font-medium",
              operator ? "text-lg" : "text-sm",
              PHASE_CLASS[phase] ?? PHASE_CLASS.initializing,
            )}
          >
            {PHASE_LABEL[phase] ?? phase}
            {status?.fault && status.fault_code ? ` #${status.fault_code}` : ""}
          </span>
          <span className="text-xs text-muted-foreground">door {status?.door ?? "—"}</span>
          {status && !status.auto && alive && <Badge variant="outline">manual mode</Badge>}
          {status?.program && (
            <span className="text-xs text-muted-foreground">
              program <span className="font-mono text-foreground">{status.program}</span>
              {status.program_no ? <span className="font-mono"> #{status.program_no}</span> : null}
            </span>
          )}
          {status?.sequence && (
            <span className="text-xs text-amber-700 dark:text-amber-300">
              {status.sequence}
              {status.detail ? ` — ${status.detail}` : ""}
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {ACTIONS.map((a) => {
            const phaseOk = a.phases === null || a.phases.includes(phase);
            return (
              <Button
                key={a.name}
                variant={a.name === "start_wash" ? "default" : "outline"}
                size="sm"
                className={btn}
                disabled={!canCommand || !alive || busy || !phaseOk}
                title={!canCommand ? "Acquire control first" : !phaseOk ? `not in ${phase}` : ""}
                onClick={() => void run(a.name)}
              >
                {a.label}
              </Button>
            );
          })}
          {!operator && (
            <Input
              value={programNo}
              placeholder="program #"
              className="h-8 w-24 font-mono text-xs"
              disabled={!canCommand}
              onChange={(ev) => setProgramNo(ev.target.value)}
              title="WashProgram number sent with 'Close & start wash' (blank = leave as is)"
            />
          )}
          <Button
            variant="destructive"
            size="sm"
            className={cn(btn, "ml-auto")}
            disabled={!canCommand || !alive}
            title="Release door permission: a travelling door stops (cancels the running action)"
            onClick={() => void cancel()}
          >
            Stop door
          </Button>
        </div>

        {error !== null && <p className="text-sm text-destructive">{error}</p>}

        {showRecipe && session !== null && alive && (
          <RecipeEditor session={session} realm={realm} rid={rid} clientId={clientId} canCommand={canCommand} phase={phase} />
        )}
      </CardContent>
    </Card>
  );
}

// ── recipe editor ────────────────────────────────────────────────────────────

const STEP_FIELDS: (keyof RecipeStep)[] = ["cleaning", "time_s", "movement", "additional", "pump_off"];

function RecipeEditor({
  session,
  realm,
  rid,
  clientId,
  canCommand,
  phase,
}: {
  session: Session;
  realm: string;
  rid: string;
  clientId: string;
  canCommand: boolean;
  phase: string;
}) {
  const [open, setOpen] = useState(false);
  const [schema, setSchema] = useState<RecipeSchema | null>(null);
  const [draft, setDraft] = useState<Recipe | null>(null);
  const [dirty, setDirty] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setMsg(null);
    try {
      const reply = await washerGetRecipe(session, realm, rid);
      if (!reply.ok || reply.recipe === undefined) {
        setMsg(`read failed: ${reply.error ?? "unknown"}`);
        return;
      }
      setSchema(reply.schema ?? null);
      setDraft(reply.recipe);
      setDirty(false);
    } catch (e) {
      setMsg(`read failed: ${String(e)}`);
    }
  }, [session, realm, rid]);


  const save = async () => {
    if (draft === null) return;
    setMsg(null);
    try {
      const ack = await washerSetRecipe(session, realm, rid, clientId, draft);
      if (!ack.ok) {
        setMsg(`write failed: ${ack.error ?? "unknown"}`);
        return;
      }
      setMsg("written to the machine");
      setDirty(false);
    } catch (e) {
      setMsg(`write failed: ${String(e)}`);
    }
  };

  const setStep = (i: number, field: keyof RecipeStep, raw: string | boolean) => {
    setDraft((d) => {
      if (d === null) return d;
      const steps = d.steps.map((s, k) => {
        if (k !== i) return s;
        if (field === "pump_off") return { ...s, pump_off: Boolean(raw) };
        const n = Number(raw);
        return { ...s, [field]: Number.isFinite(n) ? Math.trunc(n) : 0 };
      });
      return { ...d, steps };
    });
    setDirty(true);
  };

  const usedSteps = useMemo(() => {
    if (draft === null) return 0;
    let last = 0;
    draft.steps.forEach((s, i) => {
      if (s.cleaning > 0 || s.time_s > 0) last = i + 1;
    });
    return last;
  }, [draft]);

  return (
    <div className="border-t border-border/60 pt-2">
      <button
        type="button"
        className="text-xs font-medium tracking-wide text-muted-foreground hover:underline"
        onClick={() => {
          if (!open && draft === null) void load();
          setOpen((v) => !v);
        }}
      >
        {open ? "▾" : "▸"} RECIPE (wash program on the machine)
      </button>
      {open && draft !== null && (
        <div className="mt-2 space-y-2 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Name</span>
            <Input
              value={draft.name}
              className="h-7 w-56 font-mono text-xs"
              disabled={!canCommand}
              onChange={(ev) => {
                setDraft({ ...draft, name: ev.target.value });
                setDirty(true);
              }}
            />
            <span className="text-xs text-muted-foreground">{usedSteps} of {draft.steps.length} steps used</span>
            <Button variant="outline" size="sm" className="ml-auto h-7" onClick={() => void load()}>
              Reload
            </Button>
            <Button size="sm" className="cmd h-7" disabled={!canCommand || !dirty || phase === "washing"} onClick={() => void save()}
              title={phase === "washing" ? "not while washing" : ""}>
              Write to machine
            </Button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-muted-foreground">
                <tr className="[&>th]:py-1 [&>th]:text-left [&>th]:font-medium">
                  <th className="w-8">#</th>
                  {STEP_FIELDS.map((f) => (
                    <th key={f} title={schema?.step_fields[f] ? rangeHint(schema.step_fields[f]) : ""}>
                      {schema?.step_fields[f]?.title ?? f}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {draft.steps.map((s, i) => (
                  <tr key={i} className={cn("border-t border-border/60", i >= usedSteps && "text-muted-foreground/60")}>
                    <td className="py-0.5 font-mono">{i + 1}</td>
                    {STEP_FIELDS.map((f) =>
                      f === "pump_off" ? (
                        <td key={f}>
                          <input type="checkbox" checked={s.pump_off} disabled={!canCommand} onChange={(ev) => setStep(i, f, ev.target.checked)} />
                        </td>
                      ) : (
                        <td key={f}>
                          <Input
                            value={String(s[f])}
                            className="h-6 w-16 font-mono text-xs"
                            disabled={!canCommand}
                            onChange={(ev) => setStep(i, f, ev.target.value)}
                          />
                        </td>
                      ),
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {schema && Object.keys(schema.params).length > 0 && (
            <div className="grid grid-cols-2 gap-x-4 gap-y-1 md:grid-cols-3">
              {Object.entries(schema.params).map(([name, spec]) => (
                <label key={name} className="flex items-center gap-2 text-xs" title={rangeHint(spec)}>
                  <span className="flex-1 truncate text-muted-foreground" title={spec.title}>{spec.title || name}</span>
                  <Input
                    value={String(draft.params[name] ?? 0)}
                    className="h-6 w-20 font-mono text-xs"
                    disabled={!canCommand}
                    onChange={(ev) => {
                      const n = Number(ev.target.value);
                      setDraft({ ...draft, params: { ...draft.params, [name]: Number.isFinite(n) ? Math.trunc(n) : 0 } });
                      setDirty(true);
                    }}
                  />
                  {spec.unit && <span className="w-8 text-muted-foreground">{spec.unit}</span>}
                </label>
              ))}
            </div>
          )}
          {msg !== null && <p className={cn("text-xs", msg.includes("failed") ? "text-destructive" : "text-muted-foreground")}>{msg}</p>}
        </div>
      )}
      {open && draft === null && <p className="mt-1 text-xs text-muted-foreground">{msg ?? "loading…"}</p>}
    </div>
  );
}

function rangeHint(spec: { min?: number; max?: number; choices?: number[]; unit?: string }): string {
  if (spec.choices) return `one of ${spec.choices.join(", ")}`;
  if (spec.min !== undefined || spec.max !== undefined) return `${spec.min ?? "…"} – ${spec.max ?? "…"}${spec.unit ? ` ${spec.unit}` : ""}`;
  return "";
}
