// Operator page (`#/cell/hmi`, program-layer RFC §7.2): the unit state, big
// PackML buttons, e-stop status, the loaded program's state and last error.
// No scene editing, no jogging — the engineering workspace lives at #/cell/<tool>.
import { useMemo, useState } from "react";
import { Badge } from "../catalyst/badge";
import { Button } from "../catalyst/button";
import { ProgramGraphCard } from "../components/ProgramGraphCard";
import { WasherCard } from "../components/WasherCard";
import { programEvent } from "../lib/actions";
import { useProgram } from "../runtime/useProgram";
import { useRuntime } from "../runtime/context";
import { CommandBar, UnitBadge } from "./ProgramsPage";

/** Operator buttons: one per event the running program is waiting for
 * (`waiting_for[kind=event]`), labelled by the program's `hmi` map. */
function OperatorEvents({
  session,
  realm,
  state,
  labels,
  onError,
}: {
  session: import("@eclipse-zenoh/zenoh-ts").Session | null;
  realm: string;
  state: import("../lib/messages").ProgramState | null;
  labels: Record<string, string>;
  onError: (message: string | null) => void;
}) {
  const events = useMemo(() => {
    if (state === null || state.unit !== "execute") return [];
    const seen = new Set<string>();
    const out: string[] = [];
    for (const w of state.waiting_for ?? []) {
      if (w.kind === "event" && typeof w.event === "string" && !seen.has(w.event)) {
        seen.add(w.event);
        out.push(w.event);
      }
    }
    return out;
  }, [state]);
  if (events.length === 0) return null;
  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-zinc-950/5 dark:bg-zinc-900 dark:ring-white/10">
      <div className="mb-3 text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">
        Program is waiting for you
      </div>
      <div className="flex flex-wrap gap-3">
        {events.map((ev) => (
          <Button
            key={ev}
            color="blue"
            className="cmd"
            disabled={session === null}
            onClick={() => {
              if (session === null) return;
              void programEvent(session, realm, ev)
                .then(() => onError(null))
                .catch((e) => onError(`event ${ev}: ${e instanceof Error ? e.message : String(e)}`));
            }}
          >
            {labels[ev] ?? ev}
          </Button>
        ))}
      </div>
    </section>
  );
}

export default function HmiPage({ onExit }: { onExit: () => void }) {
  const runtime = useRuntime();
  const program = useProgram(runtime.session, runtime.prefix);
  const [error, setError] = useState<string | null>(null);
  const alive = runtime.wsConnected && program.alive;
  const state = program.state;
  const safety = runtime.status?.estop ? "E-STOP" : runtime.status?.protective_stop ? "PROTECTIVE STOP" : null;
  const devices = runtime.devices?.devices ?? [];
  const washers = devices.filter((d) => d.contract === "washer" && d.active !== "off");
  const hmiLabels = useMemo(() => {
    const entry = program.catalog?.programs.find((p) => p.name === state?.program);
    return entry?.hmi ?? {};
  }, [program.catalog, state?.program]);

  return (
    <div className="flex h-full min-h-0 flex-col bg-zinc-100 dark:bg-zinc-950">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-zinc-950/5 bg-white px-4 dark:border-white/10 dark:bg-zinc-900">
        <span className="text-sm font-semibold text-zinc-950 dark:text-white">{runtime.cellName}</span>
        <Badge color="zinc">Operator</Badge>
        <span className="ml-auto flex items-center gap-2 text-xs text-zinc-500 dark:text-zinc-400">
          <span>Bridge</span>
          <Badge color={runtime.wsConnected ? "emerald" : "red"}>{runtime.wsConnected ? "connected" : "offline"}</Badge>
          <Button outline onClick={() => void runtime.connect()} disabled={runtime.connecting}>
            {runtime.connecting ? "Connecting…" : runtime.wsConnected ? "Reconnect" : "Connect"}
          </Button>
          <Button plain onClick={onExit} title="Engineering workspace">
            Workspace
          </Button>
        </span>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-4">
        <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-zinc-950/5 dark:bg-zinc-900 dark:ring-white/10">
          <div className="flex items-center gap-3">
            <div className="text-xs font-medium uppercase tracking-wide text-zinc-500 dark:text-zinc-400">Unit</div>
            <UnitBadge state={state} alive={alive} />
            {safety !== null && <Badge color="red">{safety}</Badge>}
            {!alive && runtime.wsConnected && (
              <span className="text-xs text-red-600 dark:text-red-400">program runner not alive</span>
            )}
          </div>
          <div className="mt-2 font-mono text-2xl text-zinc-950 dark:text-white">
            {state?.program ?? "no program loaded"}
          </div>
          <div className="mt-1 font-mono text-sm text-zinc-500 dark:text-zinc-400">
            {state && state.program_states.length ? state.program_states.join(", ") : "—"}
            {state && state.actions.length ? `  ·  running: ${state.actions.join(", ")}` : ""}
            {state ? `  ·  cycle ${state.cycle}` : ""}
          </div>
          {state?.reason && (
            <div className="mt-2 rounded-md bg-red-50 px-3 py-2 font-mono text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">
              {state.reason}
            </div>
          )}
        </section>

        {state?.program && program.catalog && (
          <ProgramGraphCard
            session={runtime.session}
            realm={runtime.prefix ?? "cell"}
            entries={program.catalog.programs}
            state={alive ? state : null}
            transitions={program.transitions}
            compact
            height={220}
            onError={setError}
          />
        )}

        <OperatorEvents
          session={runtime.session}
          realm={runtime.prefix ?? "cell"}
          state={state}
          labels={hmiLabels}
          onError={setError}
        />

        {washers.map((w) => (
          <WasherCard
            key={w.id}
            session={runtime.session}
            realm={runtime.prefix ?? "cell"}
            rid={w.id}
            active={w.active}
            clientId={runtime.clientId}
            canCommand={runtime.commandsEnabled && runtime.holdsControl}
            operator
          />
        ))}

        <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-zinc-950/5 dark:bg-zinc-900 dark:ring-white/10">
          <CommandBar
            session={runtime.session}
            realm={runtime.prefix ?? "cell"}
            state={state}
            alive={alive}
            commands={["start", "hold", "unhold", "stop", "reset", "clear", "abort"]}
            onError={setError}
            size="lg"
          />
          {error !== null && <p className="mt-2 text-sm text-red-600 dark:text-red-400">{error}</p>}
          <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
            Load and configure programs in the engineering workspace (Programs tool). While a program
            runs it holds the cell control lease.
          </p>
        </section>

        <section className="rounded-2xl bg-white p-4 text-xs text-zinc-500 shadow-sm ring-1 ring-zinc-950/5 dark:bg-zinc-900 dark:text-zinc-400 dark:ring-white/10">
          <div className="flex flex-wrap gap-x-6 gap-y-1">
            <span>
              Control:{" "}
              <span className="font-mono text-zinc-950 dark:text-white">
                {runtime.controlOwner?.owner?.user ?? "released"}
              </span>
            </span>
            <span>
              Driver:{" "}
              <span className="font-mono text-zinc-950 dark:text-white">{runtime.driverAlive ? "alive" : "down"}</span>
            </span>
            <span>
              Speed:{" "}
              <span className="font-mono text-zinc-950 dark:text-white">
                {runtime.status ? `${Math.round(runtime.status.speed_scale * 100)}%` : "—"}
              </span>
            </span>
          </div>
        </section>
      </main>
    </div>
  );
}
