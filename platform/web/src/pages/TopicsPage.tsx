import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { Sample, Session } from "@eclipse-zenoh/zenoh-ts";
import { CongestionControl, Priority, SampleKind } from "@eclipse-zenoh/zenoh-ts";
import {
  ArrowLeft,
  CirclePause,
  CirclePlay,
  Download,
  RadioTower,
  Search,
  Trash2,
} from "lucide-react";
import { Badge } from "../catalyst/badge";
import { Button } from "../catalyst/button";
import { Input } from "../catalyst/input";
import { queryRawAll, subscribeRaw, type Unsubscribe } from "../lib/bus";
import { decodeBytes } from "../lib/codec";

const MAX_EVENTS = 500;
const MAX_PENDING = 2000;
const MAX_DECODE_BYTES = 64 * 1024;
const HEX_PREVIEW_BYTES = 256;

interface PayloadView {
  format: "CBOR" | "text" | "hex" | "empty" | "omitted";
  text: string;
}

interface TopicEvent {
  id: number;
  key: string;
  kind: "PUT" | "DELETE";
  encoding: string;
  payloadSize: number;
  attachmentSize: number;
  payload: PayloadView;
  attachment: PayloadView | null;
  receivedAt: number;
  sourceTimestamp: string | null;
  priority: string;
  congestionControl: string;
  express: boolean;
  source: "stream" | "snapshot";
}

interface TopicSummary {
  key: string;
  count: number;
  rate: number;
  payloadSize: number;
  encoding: string;
  kind: "PUT" | "DELETE";
}

interface MutableTopicSummary extends Omit<TopicSummary, "rate"> {
  arrivals: number[];
}

function enumLabel(
  values: Record<string, string | number>,
  value: number,
): string {
  const label = values[value];
  return typeof label === "string" ? label : String(value);
}

function jsonText(value: unknown): string {
  const encoded = JSON.stringify(
    value,
    (_key, current: unknown) => {
      if (typeof current === "bigint") return `${current}n`;
      if (current instanceof Uint8Array) {
        return `<Uint8Array ${current.byteLength} bytes>`;
      }
      if (current instanceof Map) return Object.fromEntries(current);
      return current;
    },
    2,
  );
  return encoded ?? String(value);
}

function hexText(bytes: Uint8Array): string {
  const shown = bytes.subarray(0, HEX_PREVIEW_BYTES);
  const rows: string[] = [];
  for (let offset = 0; offset < shown.length; offset += 16) {
    const chunk = shown.subarray(offset, offset + 16);
    const hex = Array.from(chunk, (value) => value.toString(16).padStart(2, "0")).join(" ");
    const ascii = Array.from(chunk, (value) =>
      value >= 32 && value <= 126 ? String.fromCharCode(value) : ".",
    ).join("");
    rows.push(`${offset.toString(16).padStart(4, "0")}  ${hex.padEnd(47)}  ${ascii}`);
  }
  if (bytes.length > shown.length) {
    rows.push(`… ${bytes.length - shown.length} more bytes`);
  }
  return rows.join("\n");
}

function inspectBytes(bytes: Uint8Array, encoding: string): PayloadView {
  if (bytes.length === 0) return { format: "empty", text: "(empty)" };
  if (bytes.length > MAX_DECODE_BYTES) {
    return {
      format: "omitted",
      text: `Payload preview omitted (${bytes.length.toLocaleString()} bytes).`,
    };
  }

  const normalized = encoding.toLowerCase();
  const textual =
    normalized.startsWith("text/") ||
    normalized.includes("json") ||
    normalized.includes("yaml") ||
    normalized.includes("xml") ||
    normalized.includes("javascript") ||
    normalized.includes("csv") ||
    normalized === "zenoh/string";
  if (textual) {
    return { format: "text", text: new TextDecoder().decode(bytes) };
  }

  if (
    normalized === "zenoh/bytes" ||
    normalized === "zenoh/serialized" ||
    normalized.includes("cbor")
  ) {
    try {
      return { format: "CBOR", text: jsonText(decodeBytes(bytes)) };
    } catch {
      // The platform uses CBOR on zenoh/bytes, but arbitrary third-party
      // topics may not. Fall through to an honest byte preview.
    }
  }

  return { format: "hex", text: hexText(bytes) };
}

function inspectSample(
  sample: Sample,
  id: number,
  source: TopicEvent["source"],
): TopicEvent {
  const encoding = sample.encoding().toString();
  const payload = sample.payload();
  const attachment = sample.attachment();
  const payloadSize = payload.len();
  const attachmentSize = attachment?.len() ?? 0;
  const timestamp = sample.timestamp();
  return {
    id,
    key: sample.keyexpr().toString(),
    kind: sample.kind() === SampleKind.DELETE ? "DELETE" : "PUT",
    encoding,
    payloadSize,
    attachmentSize,
    payload:
      payloadSize > MAX_DECODE_BYTES
        ? {
            format: "omitted",
            text: `Payload preview omitted (${payloadSize.toLocaleString()} bytes).`,
          }
        : inspectBytes(payload.toBytes(), encoding),
    attachment:
      attachment === undefined
        ? null
        : inspectBytes(attachment.toBytes(), "zenoh/bytes"),
    receivedAt: Date.now(),
    sourceTimestamp: timestamp?.asDate().toISOString() ?? null,
    priority: enumLabel(Priority, sample.priority()),
    congestionControl: enumLabel(
      CongestionControl,
      sample.congestionControl(),
    ),
    express: sample.express(),
    source,
  };
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

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MiB`;
}

export default function TopicsPage({
  session,
  wsConnected,
  compact = false,
}: {
  session: Session | null;
  wsConnected: boolean;
  compact?: boolean;
}) {
  const [filterDraft, setFilterDraft] = useState("**");
  const [activeFilter, setActiveFilter] = useState("**");
  const [running, setRunning] = useState(true);
  const [snapshotting, setSnapshotting] = useState(false);
  const [events, setEvents] = useState<TopicEvent[]>([]);
  const [topics, setTopics] = useState<TopicSummary[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const sequence = useRef(0);
  const pending = useRef<TopicEvent[]>([]);
  const topicState = useRef(new Map<string, MutableTopicSummary>());

  const receive = useCallback(
    (sample: Sample, source: TopicEvent["source"] = "stream") => {
      const event = inspectSample(sample, ++sequence.current, source);
      pending.current.push(event);
      if (pending.current.length > MAX_PENDING) {
        pending.current.splice(0, pending.current.length - MAX_PENDING);
      }
      const previous = topicState.current.get(event.key);
      const arrivals = previous?.arrivals ?? [];
      arrivals.push(event.receivedAt);
      const cutoff = event.receivedAt - 1000;
      while (arrivals[0] !== undefined && arrivals[0] < cutoff) arrivals.shift();
      topicState.current.set(event.key, {
        key: event.key,
        count: (previous?.count ?? 0) + 1,
        payloadSize: event.payloadSize,
        encoding: event.encoding,
        kind: event.kind,
        arrivals,
      });
    },
    [],
  );

  useEffect(() => {
    const timer = setInterval(() => {
      const batch = pending.current.splice(0);
      if (batch.length > 0) {
        const newest = [...batch].reverse();
        setEvents((previous) => [...newest, ...previous].slice(0, MAX_EVENTS));
        if (!compact) {
          setSelectedId((current) => current ?? newest[0]?.id ?? null);
        }
      }
      const now = Date.now();
      // Map iteration preserves first-seen order, so live updates never move a
      // topic out from under the operator's pointer.
      const nextTopics = [...topicState.current.values()]
        .map((topic) => {
          const cutoff = now - 1000;
          while (
            topic.arrivals[0] !== undefined &&
            topic.arrivals[0] < cutoff
          ) {
            topic.arrivals.shift();
          }
          return {
            key: topic.key,
            count: topic.count,
            rate: topic.arrivals.length,
            payloadSize: topic.payloadSize,
            encoding: topic.encoding,
            kind: topic.kind,
          };
        });
      setTopics(nextTopics);
    }, 250);
    return () => clearInterval(timer);
  }, [compact]);

  useEffect(() => {
    if (session === null || !running) return;
    let disposed = false;
    let unsubscribe: Unsubscribe | null = null;
    void subscribeRaw(session, activeFilter, (sample) => receive(sample), 1024)
      .then((next) => {
        if (disposed) next();
        else unsubscribe = next;
      })
      .catch((reason: unknown) => {
        if (!disposed) {
          setError(reason instanceof Error ? reason.message : String(reason));
          setRunning(false);
        }
      });
    return () => {
      disposed = true;
      unsubscribe?.();
    };
  }, [session, running, activeFilter, receive]);

  const clear = () => {
    pending.current = [];
    topicState.current.clear();
    setEvents([]);
    setTopics([]);
    setSelectedId(null);
    setSelectedTopic(null);
  };

  const applyFilter = () => {
    const next = filterDraft.trim();
    if (next === "") return;
    setError(null);
    setSelectedTopic(null);
    setActiveFilter(next);
    setRunning(true);
  };

  const snapshot = async () => {
    if (session === null || snapshotting) return;
    setSnapshotting(true);
    setError(null);
    try {
      const samples = await queryRawAll(session, activeFilter);
      for (const sample of samples) receive(sample, "snapshot");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setSnapshotting(false);
    }
  };

  const visibleEvents = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return events.filter((event) => {
      if (selectedTopic !== null && event.key !== selectedTopic) return false;
      if (needle === "") return true;
      return (
        event.key.toLowerCase().includes(needle) ||
        event.encoding.toLowerCase().includes(needle) ||
        event.payload.text.toLowerCase().includes(needle)
      );
    });
  }, [events, search, selectedTopic]);

  const selected =
    visibleEvents.find((event) => event.id === selectedId) ??
    visibleEvents[0] ??
    null;
  const sampleCount = topics.reduce((total, topic) => total + topic.count, 0);

  return (
    <div className="flex h-full min-h-0 bg-white dark:bg-zinc-900">
      <aside className={compact ? "hidden" : "hidden h-full w-64 shrink-0 flex-col border-r border-zinc-950/5 xl:flex dark:border-white/10"}>
        <div className="border-b border-zinc-950/5 px-4 py-3 dark:border-white/10">
          <div className="flex items-center gap-2">
            <RadioTower className="size-4 text-zinc-500 dark:text-zinc-400" />
            <h2 className="text-sm/6 font-semibold text-zinc-950 dark:text-white">
              Observed topics
            </h2>
          </div>
          <p className="mt-0.5 text-xs/5 text-zinc-500 dark:text-zinc-400">
            {topics.length} keys · {sampleCount.toLocaleString()} samples
          </p>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          <button
            type="button"
            onClick={() => setSelectedTopic(null)}
            className={`mb-1 w-full rounded-lg px-2.5 py-2 text-left text-sm/5 font-medium ${
              selectedTopic === null
                ? "bg-blue-500/10 text-blue-700 dark:text-blue-300"
                : "text-zinc-700 hover:bg-zinc-950/5 dark:text-zinc-300 dark:hover:bg-white/5"
            }`}
          >
            All topics
          </button>
          {topics.map((topic) => (
            <button
              type="button"
              key={topic.key}
              onClick={() => setSelectedTopic(topic.key)}
              className={`mb-1 w-full rounded-lg px-2.5 py-2 text-left transition ${
                selectedTopic === topic.key
                  ? "bg-blue-500/10 ring-1 ring-blue-500/20"
                  : "hover:bg-zinc-950/5 dark:hover:bg-white/5"
              }`}
            >
              <span className="block break-all font-mono text-xs/4 text-zinc-950 dark:text-white">
                {topic.key}
              </span>
              <span className="mt-1 flex items-center gap-2 text-[11px]/4 text-zinc-500 dark:text-zinc-400">
                <span>{topic.rate} Hz</span>
                <span>{formatBytes(topic.payloadSize)}</span>
                <span className="ml-auto">{topic.count.toLocaleString()}</span>
              </span>
            </button>
          ))}
          {topics.length === 0 && (
            <p className="px-2 py-6 text-center text-xs/5 text-zinc-500 dark:text-zinc-400">
              {wsConnected ? "Waiting for samples…" : "Connect to observe topics."}
            </p>
          )}
        </div>
      </aside>

      <section className={`${compact && selectedId !== null ? "hidden" : "flex"} min-w-0 flex-1 flex-col`}>
        <header className="space-y-2 border-b border-zinc-950/5 p-3 dark:border-white/10">
          <div className="flex items-center gap-2">
            <Input
              value={filterDraft}
              aria-label="Zenoh key expression"
              spellCheck={false}
              className="min-w-52 flex-1 font-mono"
              onChange={(event) => setFilterDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") applyFilter();
              }}
            />
            <Button outline disabled={!wsConnected} onClick={applyFilter}>
              Apply
            </Button>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Button
              outline
              disabled={!wsConnected}
              onClick={() => setRunning((current) => !current)}
            >
              {running ? (
                <CirclePause data-slot="icon" />
              ) : (
                <CirclePlay data-slot="icon" />
              )}
              {running ? "Pause" : "Resume"}
            </Button>
            <Button
              outline
              disabled={!wsConnected || snapshotting}
              onClick={() => void snapshot()}
            >
              <Download data-slot="icon" />
              {snapshotting ? "Reading…" : "Snapshot"}
            </Button>
            <Button plain onClick={clear}>
              <Trash2 data-slot="icon" />
              Clear
            </Button>
            <Badge
              className="ml-auto"
              color={running && wsConnected ? "emerald" : "zinc"}
            >
              {running && wsConnected ? "LIVE" : "PAUSED"}
            </Badge>
          </div>
          <div className="relative">
              <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-zinc-400" />
              <Input
                value={search}
                aria-label="Search observed samples"
                placeholder="Search keys or payloads"
                className="pl-8"
                onChange={(event) => setSearch(event.target.value)}
              />
          </div>
          {error !== null && (
            <p className="text-xs/5 text-red-600 dark:text-red-400">{error}</p>
          )}
        </header>

        <div className="min-h-0 flex-1 overflow-auto">
          <table className="w-full min-w-full border-collapse text-left text-xs/5 2xl:min-w-[720px]">
            <thead className="sticky top-0 z-10 bg-zinc-50 text-zinc-500 dark:bg-zinc-950 dark:text-zinc-400">
              <tr>
                <th className="border-b border-zinc-950/5 px-3 py-2 font-medium dark:border-white/10">Received</th>
                <th className="border-b border-zinc-950/5 px-3 py-2 font-medium dark:border-white/10">Kind</th>
                <th className="border-b border-zinc-950/5 px-3 py-2 font-medium dark:border-white/10">Key expression</th>
                <th className="hidden border-b border-zinc-950/5 px-3 py-2 font-medium 2xl:table-cell dark:border-white/10">Encoding</th>
                <th className="hidden border-b border-zinc-950/5 px-3 py-2 text-right font-medium 2xl:table-cell dark:border-white/10">Size</th>
              </tr>
            </thead>
            <tbody className="font-mono text-zinc-700 dark:text-zinc-300">
              {visibleEvents.map((event) => (
                <tr
                  key={event.id}
                  onClick={() => setSelectedId(event.id)}
                  className={`cursor-default border-b border-zinc-950/5 hover:bg-zinc-950/2.5 dark:border-white/5 dark:hover:bg-white/5 ${
                    selected?.id === event.id ? "bg-blue-500/10" : ""
                  }`}
                >
                  <td className="whitespace-nowrap px-3 py-2 tabular-nums">{formatClock(event.receivedAt)}</td>
                  <td className="px-3 py-2">
                    <span className={event.kind === "DELETE" ? "text-red-600 dark:text-red-400" : "text-emerald-700 dark:text-emerald-400"}>
                      {event.kind}
                    </span>
                  </td>
                  <td className="max-w-md break-all px-3 py-2 text-zinc-950 dark:text-white">{event.key}</td>
                  <td className="hidden whitespace-nowrap px-3 py-2 text-zinc-500 2xl:table-cell dark:text-zinc-400">{event.encoding}</td>
                  <td className="hidden whitespace-nowrap px-3 py-2 text-right tabular-nums 2xl:table-cell">{formatBytes(event.payloadSize)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {visibleEvents.length === 0 && (
            <div className="flex h-48 items-center justify-center text-sm/6 text-zinc-500 dark:text-zinc-400">
              {wsConnected ? "No matching samples yet." : "Connect to inspect raw topics."}
            </div>
          )}
        </div>
      </section>

      <aside className={compact ? (selectedId === null ? "hidden" : "flex h-full w-full flex-col") : "hidden h-full w-96 shrink-0 flex-col border-l border-zinc-950/5 md:flex dark:border-white/10"}>
        <div className="border-b border-zinc-950/5 px-4 py-3 dark:border-white/10">
          <div className="flex items-center gap-2">
            {compact && selectedId !== null && (
              <Button plain onClick={() => setSelectedId(null)}>
                <ArrowLeft data-slot="icon" />
                Back
              </Button>
            )}
            <div>
              <h2 className="text-sm/6 font-semibold text-zinc-950 dark:text-white">Sample detail</h2>
              <p className="mt-0.5 text-xs/5 text-zinc-500 dark:text-zinc-400">Metadata and bounded raw payload preview</p>
            </div>
          </div>
        </div>
        {selected === null ? (
          <div className="flex flex-1 items-center justify-center p-6 text-center text-sm/6 text-zinc-500 dark:text-zinc-400">
            Select a sample from the stream.
          </div>
        ) : (
          <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
            <section>
              <h3 className="break-all font-mono text-sm/5 font-medium text-zinc-950 dark:text-white">{selected.key}</h3>
              <div className="mt-2 flex flex-wrap gap-1.5">
                <Badge color={selected.kind === "DELETE" ? "red" : "emerald"}>{selected.kind}</Badge>
                <Badge color={selected.source === "snapshot" ? "amber" : "blue"}>{selected.source}</Badge>
                <Badge color="zinc">{selected.payload.format}</Badge>
              </div>
            </section>

            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 font-mono text-xs/5">
              <dt className="text-zinc-500 dark:text-zinc-400">received</dt>
              <dd>{new Date(selected.receivedAt).toISOString()}</dd>
              <dt className="text-zinc-500 dark:text-zinc-400">timestamp</dt>
              <dd className="break-all">{selected.sourceTimestamp ?? "—"}</dd>
              <dt className="text-zinc-500 dark:text-zinc-400">encoding</dt>
              <dd className="break-all">{selected.encoding}</dd>
              <dt className="text-zinc-500 dark:text-zinc-400">payload</dt>
              <dd>{formatBytes(selected.payloadSize)}</dd>
              <dt className="text-zinc-500 dark:text-zinc-400">attachment</dt>
              <dd>{formatBytes(selected.attachmentSize)}</dd>
              <dt className="text-zinc-500 dark:text-zinc-400">priority</dt>
              <dd>{selected.priority}</dd>
              <dt className="text-zinc-500 dark:text-zinc-400">congestion</dt>
              <dd>{selected.congestionControl}</dd>
              <dt className="text-zinc-500 dark:text-zinc-400">express</dt>
              <dd>{String(selected.express)}</dd>
            </dl>

            <section>
              <h3 className="mb-2 text-xs/6 font-medium text-zinc-500 dark:text-zinc-400">Payload · {selected.payload.format}</h3>
              <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-zinc-950/5 p-3 font-mono text-xs/5 text-zinc-800 ring-1 ring-zinc-950/5 dark:bg-black/25 dark:text-zinc-200 dark:ring-white/10">
                {selected.payload.text}
              </pre>
            </section>

            {selected.attachment !== null && (
              <section>
                <h3 className="mb-2 text-xs/6 font-medium text-zinc-500 dark:text-zinc-400">Attachment · {selected.attachment.format}</h3>
                <pre className="max-h-72 overflow-auto whitespace-pre-wrap break-all rounded-lg bg-zinc-950/5 p-3 font-mono text-xs/5 text-zinc-800 ring-1 ring-zinc-950/5 dark:bg-black/25 dark:text-zinc-200 dark:ring-white/10">
                  {selected.attachment.text}
                </pre>
              </section>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}
