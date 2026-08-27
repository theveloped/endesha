// Full-page service logs (`#/cell/logs`): every supervised child's captured
// stdout/stderr plus the supervisor's lifecycle events, merged into one tail.
// Late joiners get the supervisor's ring buffers (the log keys and the events
// key are queryable); after that the live subscription streams. Left rail
// filters by source; the toolbar filters by level and text.
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { CirclePause, CirclePlay, ScrollText, Trash2 } from "lucide-react";
import { Badge } from "../catalyst/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { query, queryAll, subscribeLatest, type Unsubscribe } from "../lib/bus";
import { supervisorEvents, supervisorLogGlob } from "../lib/config";
import type { ServiceLogLine, SupervisorEvent } from "../lib/messages";

const MAX_ENTRIES = 2000;
const EVENTS_SOURCE = "events";

interface Entry {
  id: number;
  t: number; // ms epoch
  source: string; // service name, or "events"
  level: string;
  stream: string | null;
  message: string;
  event: boolean;
}

function toMs(t: number | bigint): number {
  return Number(t) / 1e6;
}

function formatClock(value: number): string {
  return new Date(value).toLocaleTimeString(undefined, {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    fractionalSecondDigits: 3,
  });
}

function eventMessage(ev: SupervisorEvent): string {
  const extras = Object.entries(ev)
    .filter(([k]) => !["t", "kind", "service"].includes(k))
    .filter(([, v]) => v !== undefined && v !== null)
    .map(([k, v]) => `${k}=${String(v)}`)
    .join(" ");
  return extras === "" ? ev.kind : `${ev.kind} ${extras}`;
}

function eventLevel(ev: SupervisorEvent): string {
  if (ev.kind === "spawn_failed" || ev.ok === false) return "error";
  if (ev.kind === "service_exited") return "warning";
  return "info";
}

const LEVEL_STYLES: Record<string, string> = {
  debug: "text-zinc-400 dark:text-zinc-500",
  info: "text-zinc-700 dark:text-zinc-300",
  warning: "text-amber-700 dark:text-amber-400",
  error: "text-red-600 dark:text-red-400",
};

const LEVEL_ORDER: Record<string, number> = { debug: 0, info: 1, warning: 2, error: 3 };
const LEVELS = ["debug", "info", "warning", "error"] as const;

export default function LogsPage({
  session,
  realm,
  wsConnected,
}: {
  session: Session | null;
  realm: string;
  wsConnected: boolean;
}) {
  const [entries, setEntries] = useState<Entry[]>([]);
  const [selectedSource, setSelectedSource] = useState<string | null>(null);
  const [minLevel, setMinLevel] = useState<(typeof LEVELS)[number]>("debug");
  const [search, setSearch] = useState("");
  const [running, setRunning] = useState(true);
  const [bufferedCount, setBufferedCount] = useState(0);
  const sequence = useRef(0);
  const pending = useRef<Entry[]>([]);
  const runningRef = useRef(true);
  const tailRef = useRef<HTMLDivElement | null>(null);

  const push = useCallback((batch: Entry[]) => {
    if (batch.length === 0) return;
    if (!runningRef.current) {
      pending.current.push(...batch);
      if (pending.current.length > MAX_ENTRIES) {
        pending.current.splice(0, pending.current.length - MAX_ENTRIES);
      }
      setBufferedCount(pending.current.length);
      return;
    }
    setEntries((current) => {
      const next = [...current, ...batch];
      return next.length > MAX_ENTRIES ? next.slice(-MAX_ENTRIES) : next;
    });
  }, []);

  const fromLine = useCallback(
    (line: ServiceLogLine): Entry => ({
      id: ++sequence.current,
      t: toMs(line.t),
      source: line.source,
      level: line.level ?? "info",
      stream: line.stream ?? null,
      message: line.message,
      event: false,
    }),
    [],
  );

  const fromEvent = useCallback(
    (ev: SupervisorEvent): Entry => ({
      id: ++sequence.current,
      t: toMs(ev.t),
      source: EVENTS_SOURCE,
      level: eventLevel(ev),
      stream: null,
      message: `${ev.service !== null && ev.service !== undefined ? `[${ev.service}] ` : ""}${eventMessage(ev)}`,
      event: true,
    }),
    [],
  );

  useEffect(() => {
    if (session === null) return;
    let disposed = false;
    const unsubs: Unsubscribe[] = [];
    void (async () => {
      const subs = await Promise.all([
        subscribeLatest(session, supervisorLogGlob(realm), (m) => push([fromLine(m as ServiceLogLine)]), 128),
        subscribeLatest(session, supervisorEvents(realm), (m) => push([fromEvent(m as SupervisorEvent)]), 32),
      ]);
      if (disposed) {
        subs.forEach((u) => u());
        return;
      }
      unsubs.push(...subs);
      // Late joiner: the supervisor's ring buffers.
      const [rings, events] = await Promise.all([
        queryAll(session, supervisorLogGlob(realm)),
        query(session, supervisorEvents(realm), {}),
      ]);
      if (disposed) return;
      const seeded: Entry[] = [];
      for (const ring of rings) {
        const lines = ((ring.value as { lines?: ServiceLogLine[] }).lines ?? []) as ServiceLogLine[];
        seeded.push(...lines.map(fromLine));
      }
      const past = ((events as { events?: SupervisorEvent[] } | null)?.events ?? []) as SupervisorEvent[];
      seeded.push(...past.map(fromEvent));
      seeded.sort((a, b) => a.t - b.t);
      // Rings arrive after the subscription started: prepend, dedupe by (t, message).
      setEntries((current) => {
        const seen = new Set(current.map((e) => `${e.t}:${e.message}`));
        const fresh = seeded.filter((e) => !seen.has(`${e.t}:${e.message}`));
        const next = [...fresh, ...current].sort((a, b) => a.t - b.t);
        return next.length > MAX_ENTRIES ? next.slice(-MAX_ENTRIES) : next;
      });
    })();
    return () => {
      disposed = true;
      unsubs.forEach((u) => u());
    };
  }, [session, realm, push, fromLine, fromEvent]);

  const toggleRunning = () => {
    setRunning((current) => {
      const next = !current;
      runningRef.current = next;
      if (next && pending.current.length > 0) {
        const flush = pending.current;
        pending.current = [];
        setBufferedCount(0);
        setEntries((prev) => {
          const merged = [...prev, ...flush];
          return merged.length > MAX_ENTRIES ? merged.slice(-MAX_ENTRIES) : merged;
        });
      }
      return next;
    });
  };

  const sources = useMemo(() => {
    const names = new Set<string>();
    for (const e of entries) names.add(e.source);
    names.delete(EVENTS_SOURCE);
    return [...names].sort();
  }, [entries]);

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const min = LEVEL_ORDER[minLevel];
    return entries.filter((e) => {
      if (selectedSource !== null && e.source !== selectedSource) return false;
      if ((LEVEL_ORDER[e.level] ?? 1) < min) return false;
      if (needle !== "" && !e.message.toLowerCase().includes(needle) && !e.source.toLowerCase().includes(needle)) return false;
      return true;
    });
  }, [entries, selectedSource, minLevel, search]);

  // Tail: keep the newest line in view while running.
  useEffect(() => {
    if (!running) return;
    tailRef.current?.scrollIntoView({ block: "end" });
  }, [visible, running]);

  return (
    <div className="flex h-full min-h-0 bg-white dark:bg-zinc-900">
      {/* source rail */}
      <aside className="flex w-56 shrink-0 flex-col border-r border-zinc-950/5 dark:border-white/10">
        <div className="shrink-0 border-b border-zinc-950/5 px-4 py-3 dark:border-white/10">
          <div className="flex items-center gap-2">
            <ScrollText className="size-4 text-zinc-500 dark:text-zinc-400" />
            <h2 className="text-sm/6 font-semibold text-zinc-950 dark:text-white">Service logs</h2>
          </div>
          <p className="text-xs/5 text-zinc-500 dark:text-zinc-400">
            {entries.length} lines · {sources.length} services
          </p>
        </div>
        <nav className="min-h-0 flex-1 overflow-y-auto py-1 text-xs">
          {[null, ...sources, EVENTS_SOURCE].map((source) => {
            const count =
              source === null ? entries.length : entries.filter((e) => e.source === source).length;
            const label = source === null ? "All sources" : source;
            return (
              <button
                key={label}
                type="button"
                className={cn(
                  "flex w-full items-center gap-1 px-3 py-1 text-left font-mono hover:bg-muted/60",
                  selectedSource === source && "bg-muted",
                  source === EVENTS_SOURCE && "text-sky-700 dark:text-sky-300",
                )}
                onClick={() => setSelectedSource(source)}
              >
                <span className="truncate">{label}</span>
                <span className="ml-auto text-zinc-400">{count}</span>
              </button>
            );
          })}
          {sources.length === 0 && (
            <p className="px-3 py-2 text-zinc-500 dark:text-zinc-400">
              {wsConnected ? "No service logs yet — the supervisor publishes them as children print." : "Connect to stream logs."}
            </p>
          )}
        </nav>
      </aside>

      {/* tail */}
      <section className="flex min-w-0 flex-1 flex-col">
        <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-zinc-950/5 px-3 py-2 dark:border-white/10">
          <div className="flex items-center gap-1">
            {LEVELS.map((level) => (
              <button
                key={level}
                type="button"
                aria-pressed={minLevel === level}
                title={`Show ${level} and above`}
                className={cn(
                  "rounded px-1.5 py-0.5 text-[11px] font-medium capitalize",
                  minLevel === level
                    ? "bg-zinc-900 text-white dark:bg-white dark:text-zinc-900"
                    : "text-zinc-500 hover:bg-zinc-950/5 dark:text-zinc-400 dark:hover:bg-white/10",
                )}
                onClick={() => setMinLevel(level)}
              >
                {level}
              </button>
            ))}
          </div>
          <Input
            className="h-7 w-56 text-xs"
            placeholder="Search message or service"
            value={search}
            onChange={(ev) => setSearch(ev.target.value)}
          />
          <div className="ml-auto flex items-center gap-1">
            {!running && bufferedCount > 0 && <Badge color="amber">{bufferedCount} buffered</Badge>}
            <Button variant="ghost" size="sm" className="h-7" onClick={toggleRunning}>
              {running ? <CirclePause className="mr-1 size-3.5" /> : <CirclePlay className="mr-1 size-3.5" />}
              {running ? "Pause" : "Resume"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7"
              onClick={() => {
                pending.current = [];
                setBufferedCount(0);
                setEntries([]);
              }}
            >
              <Trash2 className="mr-1 size-3.5" /> Clear
            </Button>
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-auto font-mono text-xs leading-5">
          {visible.length === 0 ? (
            <div className="flex h-full items-center justify-center p-6 text-center font-sans text-sm text-zinc-500 dark:text-zinc-400">
              {wsConnected
                ? "Nothing matches — logs appear here as supervised services print."
                : "Connect to the bridge to stream service logs."}
            </div>
          ) : (
            <table className="w-full border-collapse">
              <tbody>
                {visible.map((entry) => (
                  <tr key={entry.id} className={cn("align-top", entry.event && "bg-sky-500/5")}>
                    <td className="w-24 whitespace-nowrap py-px pl-3 pr-2 tabular-nums text-zinc-400">
                      {formatClock(entry.t)}
                    </td>
                    <td className="w-36 truncate py-px pr-2 text-zinc-500 dark:text-zinc-400">
                      {entry.source}
                    </td>
                    <td className={cn("py-px pr-3 break-all whitespace-pre-wrap", LEVEL_STYLES[entry.level] ?? LEVEL_STYLES.info)}>
                      {entry.message}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div ref={tailRef} />
        </div>
      </section>
    </div>
  );
}
