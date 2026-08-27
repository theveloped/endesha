// Full-page query/reply audit (`#/cell/queries`): the command traffic a
// passive subscriber can never see. Services echo every handled command query
// onto `{realm}/audit/{service}` (wf.core.audit) — request, reply, outcome and
// duration — and this page streams those echoes live. The mechanism stays
// query/reply on the bus; the echo is pure observability, and the recorder
// captures it like any other realm topic.
import { useEffect, useMemo, useRef, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { ArrowLeftRight, CirclePause, CirclePlay, Trash2, X } from "lucide-react";
import { Badge } from "../catalyst/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { subscribeLatest, type Unsubscribe } from "../lib/bus";
import { auditGlob } from "../lib/config";
import type { AuditRecord } from "../lib/messages";

const MAX_RECORDS = 1000;

interface Row extends AuditRecord {
  id: number;
  tMs: number;
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

function pretty(value: unknown): string {
  if (value === null || value === undefined) return "—";
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export default function QueriesPage({
  session,
  wsConnected,
  realm,
}: {
  session: Session | null;
  wsConnected: boolean;
  realm: string;
}) {
  const [rows, setRows] = useState<Row[]>([]);
  const [service, setService] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [running, setRunning] = useState(true);
  const [bufferedCount, setBufferedCount] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const sequence = useRef(0);
  const runningRef = useRef(true);
  const pending = useRef<Row[]>([]);

  useEffect(() => {
    if (session === null) return;
    let disposed = false;
    let unsub: Unsubscribe | null = null;
    void (async () => {
      const next = await subscribeLatest(
        session,
        auditGlob(realm),
        (m) => {
          const record = m as AuditRecord;
          const row: Row = { ...record, id: ++sequence.current, tMs: Number(record.t) / 1e6 };
          if (!runningRef.current) {
            pending.current.push(row);
            if (pending.current.length > MAX_RECORDS) {
              pending.current.splice(0, pending.current.length - MAX_RECORDS);
            }
            setBufferedCount(pending.current.length);
            return;
          }
          setRows((current) => {
            const merged = [...current, row];
            return merged.length > MAX_RECORDS ? merged.slice(-MAX_RECORDS) : merged;
          });
        },
        128,
      );
      if (disposed) next();
      else unsub = next;
    })();
    return () => {
      disposed = true;
      unsub?.();
    };
  }, [session, realm]);

  const toggleRunning = () => {
    setRunning((current) => {
      const next = !current;
      runningRef.current = next;
      if (next && pending.current.length > 0) {
        const flush = pending.current;
        pending.current = [];
        setBufferedCount(0);
        setRows((prev) => {
          const merged = [...prev, ...flush];
          return merged.length > MAX_RECORDS ? merged.slice(-MAX_RECORDS) : merged;
        });
      }
      return next;
    });
  };

  const services = useMemo(() => [...new Set(rows.map((r) => r.service))].sort(), [rows]);

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return rows.filter((r) => {
      if (service !== null && r.service !== service) return false;
      if (needle === "") return true;
      return (
        r.key.toLowerCase().includes(needle) ||
        r.service.toLowerCase().includes(needle) ||
        pretty(r.request).toLowerCase().includes(needle)
      );
    });
  }, [rows, service, search]);

  const selected = visible.find((r) => r.id === selectedId) ?? null;

  return (
    <div className="flex h-full min-h-0 bg-white dark:bg-zinc-900">
      <section className="flex min-w-0 flex-1 flex-col">
        <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-zinc-950/5 px-3 py-2 dark:border-white/10">
          <ArrowLeftRight className="size-4 text-zinc-500 dark:text-zinc-400" />
          <h2 className="text-sm/6 font-semibold text-zinc-950 dark:text-white">Queries</h2>
          <select
            className="h-7 rounded-md border border-zinc-950/10 bg-white px-1 font-mono text-xs dark:border-white/10 dark:bg-zinc-900"
            value={service ?? ""}
            onChange={(ev) => setService(ev.target.value === "" ? null : ev.target.value)}
          >
            <option value="">all services</option>
            {services.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
          <Input
            className="h-7 w-64 text-xs"
            placeholder="Search key, service or request"
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
                setRows([]);
                setSelectedId(null);
              }}
            >
              <Trash2 className="mr-1 size-3.5" /> Clear
            </Button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-auto">
          {visible.length === 0 ? (
            <div className="flex h-full items-center justify-center p-6 text-center text-sm text-zinc-500 dark:text-zinc-400">
              {wsConnected
                ? "No command queries observed yet — send one (load a program, set an output, save a pose) and it appears here."
                : "Connect to the bridge to observe command queries."}
            </div>
          ) : (
            <table className="w-full border-collapse font-mono text-xs">
              <thead className="sticky top-0 bg-zinc-50 text-left text-zinc-500 dark:bg-zinc-950 dark:text-zinc-400">
                <tr>
                  <th className="py-1.5 pl-3 pr-2 font-medium">Received</th>
                  <th className="py-1.5 pr-2 font-medium">Service</th>
                  <th className="py-1.5 pr-2 font-medium">Key</th>
                  <th className="py-1.5 pr-2 font-medium">Outcome</th>
                  <th className="py-1.5 pr-3 text-right font-medium">ms</th>
                </tr>
              </thead>
              <tbody>
                {visible.map((row) => (
                  <tr
                    key={row.id}
                    className={cn(
                      "cursor-pointer border-t border-zinc-950/5 hover:bg-muted/60 dark:border-white/5",
                      selectedId === row.id && "bg-muted",
                    )}
                    onClick={() => setSelectedId(row.id)}
                  >
                    <td className="whitespace-nowrap py-1 pl-3 pr-2 tabular-nums text-zinc-400">
                      {formatClock(row.tMs)}
                    </td>
                    <td className="py-1 pr-2 text-zinc-500 dark:text-zinc-400">{row.service}</td>
                    <td className="max-w-0 truncate py-1 pr-2 text-zinc-950 dark:text-white" title={row.key}>
                      {row.key}
                    </td>
                    <td className="py-1 pr-2">
                      {row.ok === true ? (
                        <Badge color="emerald">ok</Badge>
                      ) : row.ok === false ? (
                        <Badge color="red">failed</Badge>
                      ) : (
                        <Badge color="zinc">—</Badge>
                      )}
                    </td>
                    <td className="py-1 pr-3 text-right tabular-nums text-zinc-500 dark:text-zinc-400">
                      {row.duration_ms.toFixed(1)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      {/* detail */}
      <aside
        className={cn(
          "h-full w-96 shrink-0 flex-col border-l border-zinc-950/5 dark:border-white/10",
          selected === null ? "hidden xl:flex" : "flex",
        )}
      >
        {selected === null ? (
          <div className="flex h-full items-center justify-center p-6 text-center text-sm text-zinc-500 dark:text-zinc-400">
            Select a query from the stream.
          </div>
        ) : (
          <>
            <header className="flex shrink-0 items-start gap-2 border-b border-zinc-950/5 px-4 py-3 dark:border-white/10">
              <div className="min-w-0 flex-1">
                <h3 className="break-all font-mono text-xs font-semibold text-zinc-950 dark:text-white">
                  {selected.key}
                </h3>
                <p className="text-xs/5 text-zinc-500 dark:text-zinc-400">
                  {selected.service} · {formatClock(selected.tMs)} · {selected.duration_ms.toFixed(1)} ms
                </p>
              </div>
              <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setSelectedId(null)}>
                <X className="size-4" />
              </Button>
            </header>
            <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4 text-xs">
              {selected.params !== null && (
                <section>
                  <h4 className="mb-1 font-medium text-zinc-500 dark:text-zinc-400">Parameters</h4>
                  <pre className="whitespace-pre-wrap break-all rounded-lg bg-zinc-950/2.5 p-2 font-mono ring-1 ring-zinc-950/5 dark:bg-white/5 dark:ring-white/10">
                    {selected.params}
                  </pre>
                </section>
              )}
              <section>
                <h4 className="mb-1 font-medium text-zinc-500 dark:text-zinc-400">Request</h4>
                <pre className="whitespace-pre-wrap break-all rounded-lg bg-zinc-950/2.5 p-2 font-mono ring-1 ring-zinc-950/5 dark:bg-white/5 dark:ring-white/10">
                  {pretty(selected.request)}
                </pre>
              </section>
              <section>
                <h4 className="mb-1 font-medium text-zinc-500 dark:text-zinc-400">Reply</h4>
                <pre className="whitespace-pre-wrap break-all rounded-lg bg-zinc-950/2.5 p-2 font-mono ring-1 ring-zinc-950/5 dark:bg-white/5 dark:ring-white/10">
                  {pretty(selected.reply)}
                </pre>
              </section>
              {selected.error !== null && (
                <section>
                  <h4 className="mb-1 font-medium text-red-600 dark:text-red-400">Handler error</h4>
                  <pre className="whitespace-pre-wrap break-all rounded-lg bg-red-500/10 p-2 font-mono text-red-700 ring-1 ring-red-500/20 dark:text-red-300">
                    {selected.error}
                  </pre>
                </section>
              )}
            </div>
          </>
        )}
      </aside>
    </div>
  );
}
