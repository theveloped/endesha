// Global replay drawer (spec §2): session picker, scrubber with mark ticks,
// play/pause, rate, data-time readout. Docked as the last grid row whenever
// realm = REPLAY. All time math is BigInt end-to-end — cbor-x decodes ns
// uint64 > 2^53 as BigInt, and a seek t_ns MUST be sent as BigInt so cbor-x
// encodes CBOR uint64 (a JS number would arrive as a float and fail the
// replayer's isinstance(t_ns, int) check). Transport controls here NEVER
// carry .cmd — only robot-command controls flatten in replay.
import { useEffect, useState, type ReactNode } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { query, subscribeLatest, type Unsubscribe } from "../lib/bus";
import { replayClock, replayCmd } from "../lib/config";
import {
  asBigInt,
  type ReplayClock,
  type ReplayInfo,
  type ReplayStatus,
} from "../lib/messages";

const RATES = ["0.25", "0.5", "1", "2", "4"];

interface ReplayDrawerProps {
  session: Session | null;
  sid: string | null;
  sessions: string[];
  onPickSession: (sid: string) => void;
}

export default function ReplayDrawer({
  session,
  sid,
  sessions,
  onPickSession,
}: ReplayDrawerProps) {
  const [info, setInfo] = useState<ReplayInfo | null>(null);
  const [clock, setClock] = useState<ReplayClock | null>(null);
  const [scrubbing, setScrubbing] = useState<number | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [cmdError, setCmdError] = useState<string | null>(null);

  // State is per-session: App keys this component on sid, so a session
  // switch remounts with fresh nulls. The effect only queries + subscribes;
  // a session reconnect re-runs it and overwrites prior results.
  useEffect(() => {
    if (session === null || sid === null) return;
    let disposed = false;
    let unsub: Unsubscribe | null = null;
    void (async () => {
      const [reply, u] = await Promise.all([
        query(session, replayCmd(sid, "info"), {}),
        subscribeLatest(
          session,
          replayClock(sid),
          (m) => setClock(m as ReplayClock),
          1,
        ),
      ]);
      if (disposed) {
        u();
        return;
      }
      unsub = u;
      // Replayer died between liveliness and query: no retry loop — the
      // liveliness watch will drop the session from the picker.
      if (reply === null || (reply as ReplayInfo).ok === false) {
        setUnavailable(true);
        setInfo(null);
      } else {
        setUnavailable(false);
        setInfo(reply as ReplayInfo);
      }
    })();
    return () => {
      disposed = true;
      if (unsub !== null) unsub();
    };
  }, [session, sid]);

  const sendCmd = async (action: string, payload: unknown) => {
    if (session === null || sid === null) return;
    setCmdError(null);
    try {
      const reply = (await query(
        session,
        replayCmd(sid, action),
        payload,
      )) as ReplayStatus | null;
      if (reply === null) {
        setCmdError(`no reply from ${action}`);
        return;
      }
      if (!reply.ok) {
        setCmdError(reply.error ?? `${action} failed`);
        return;
      }
      // Merge so the UI reacts before the next clock sample arrives.
      setClock((c) => ({
        t: c?.t ?? reply.t_data,
        t_data: reply.t_data,
        rate: reply.rate,
        playing: reply.playing,
      }));
    } catch (e) {
      setCmdError(e instanceof Error ? e.message : String(e));
    }
  };

  let body: ReactNode;
  if (sid === null) {
    body = (
      <span className="text-sm text-muted-foreground">
        select a replay session to scrub
      </span>
    );
  } else if (unavailable) {
    body = (
      <span className="text-sm text-muted-foreground">session unavailable</span>
    );
  } else if (info !== null) {
    const start = asBigInt(info.start_ns);
    const end = asBigInt(info.end_ns);
    const durMs = Number((end - start) / 1_000_000n);
    const tData = asBigInt(clock?.t_data ?? info.t_data);
    const pos = scrubbing ?? Number((tData - start) / 1_000_000n);
    const playing = clock?.playing ?? info.playing;
    const rate = clock?.rate ?? info.rate;
    const wallTime = new Date(
      Number((scrubbing === null ? tData : start + BigInt(Math.round(pos)) * 1_000_000n) / 1_000_000n),
    ).toLocaleTimeString();

    body = (
      <>
        <Button
          size="icon"
          aria-label={playing ? "pause" : "play"}
          onClick={() => void sendCmd(playing ? "pause" : "play", {})}
        >
          {playing ? "⏸" : "▶"}
        </Button>
        <div className="relative min-w-0 flex-1">
          {durMs > 0 &&
            info.marks.map((mark, i) => (
              <span
                key={i}
                title={mark.label}
                className="pointer-events-none absolute top-0 z-10 h-full w-0.5 bg-warn"
                style={{
                  left: `${(Number((asBigInt(mark.t) - start) / 1_000_000n) / durMs) * 100}%`,
                }}
              />
            ))}
          <Slider
            min={0}
            max={durMs}
            step={100}
            value={[Math.min(Math.max(pos, 0), durMs)]}
            onValueChange={(vals) => setScrubbing(vals[0])}
            onValueCommit={(vals) => {
              void sendCmd("seek", {
                t_ns: start + BigInt(Math.round(vals[0])) * 1_000_000n,
              });
              setScrubbing(null);
            }}
          />
        </div>
        <ToggleGroup
          type="single"
          value={String(rate)}
          onValueChange={(v) => {
            if (v) void sendCmd("rate", { rate: Number(v) });
          }}
        >
          {RATES.map((r) => (
            <ToggleGroupItem
              key={r}
              value={r}
              size="sm"
              className="px-2 font-mono text-xs tabular-nums data-[state=on]:bg-primary data-[state=on]:text-primary-foreground"
            >
              {r}×
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
        <span className="whitespace-nowrap font-mono text-xs tabular-nums">
          {wallTime} +{(pos / 1000).toFixed(1)}s / {(durMs / 1000).toFixed(1)}s{" "}
          {rate}×
        </span>
        <Badge
          variant="secondary"
          className={playing ? "bg-ok/20 text-ok" : "bg-warn/20 text-warn"}
        >
          {playing ? "playing" : "paused"}
        </Badge>
      </>
    );
  } else {
    body = (
      <span className="text-sm text-muted-foreground">loading session…</span>
    );
  }

  return (
    <footer className="col-span-2 flex items-center gap-3 border-t border-border bg-card px-3 py-2">
      <Select value={sid ?? undefined} onValueChange={onPickSession}>
        <SelectTrigger size="sm" className="w-44">
          <SelectValue placeholder="select session…" />
        </SelectTrigger>
        <SelectContent>
          {sessions.map((s) => (
            <SelectItem key={s} value={s}>
              {s}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {body}
      {cmdError !== null && (
        <span className="text-xs text-destructive">{cmdError}</span>
      )}
    </footer>
  );
}
