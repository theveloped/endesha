// Cameras page (camera2d cam0): live OR replayed frames render through the
// ONE image-topic subscription — stream frames, grabs, and replays are
// indistinguishable here (realm-prefix swap; App remounts via key={prefix}).
// Frames are heavy, so subscriptions are page-local: subscribe only while
// mounted, unlike the global arm subs in App. The UI renders JPEG only —
// a raw Bayer header shows a notice instead of an image.
import { useEffect, useRef, useState } from "react";
import type { Sample, Session } from "@eclipse-zenoh/zenoh-ts";
import { decode } from "cbor-x";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { query, subscribeLatest, subscribeRaw, watchAlive, type Unsubscribe } from "../lib/bus";
import { camAlive, camCmd, camImage, camStatus } from "../lib/config";
import { asBigInt, type Ack, type CameraStatus, type FrameHeader, type GrabReply } from "../lib/messages";
import type { BrowserProducerState } from "../lib/camera2d/producer";

const KV_CLASS =
  "grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 font-mono text-sm tabular-nums";

const RATE_OPTIONS = ["5", "10", "15", "30"];
const SCALE_OPTIONS = ["1", "0.5", "0.25"];
const QUALITY_OPTIONS = ["50", "75", "90"];

interface Frame {
  header: FrameHeader;
  /** Blob URL for jpeg frames; null for non-renderable encodings. */
  url: string | null;
}

interface CamerasPageProps {
  session: Session | null;
  realm: string;
  wsConnected: boolean;
  commandsEnabled: boolean;
  producer: BrowserProducerState;
}

export default function CamerasPage({
  session,
  realm,
  wsConnected,
  commandsEnabled,
  producer,
}: CamerasPageProps) {
  const [frame, setFrame] = useState<Frame | null>(null);
  const [status, setStatus] = useState<CameraStatus | null>(null);
  const [alive, setAlive] = useState(false);
  const [cmdError, setCmdError] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState(0); // 1 Hz clock for the t_capture age

  const [rate, setRate] = useState("15");
  const [scale, setScale] = useState("0.25");
  const [quality, setQuality] = useState("75");
  const [exposure, setExposure] = useState("");
  const [gain, setGain] = useState("");

  const urlRef = useRef<string | null>(null);

  useEffect(() => {
    if (session === null) return;
    const unsubs: Unsubscribe[] = [];
    let disposed = false;
    const onFrame = (sample: Sample) => {
      const att = sample.attachment();
      if (att === undefined) return; // not a contract frame — skip
      let header: FrameHeader;
      try {
        header = decode(att.toBytes()) as FrameHeader;
      } catch (e) {
        console.error("frame header decode failed:", e);
        return;
      }
      let url: string | null = null;
      if (header.encoding === "jpeg") {
        url = URL.createObjectURL(
          new Blob([sample.payload().toBytes() as BlobPart], {
            type: "image/jpeg",
          }),
        );
      }
      if (urlRef.current !== null) URL.revokeObjectURL(urlRef.current);
      urlRef.current = url;
      setNowMs(Date.now());
      setFrame({ header, url });
    };
    void (async () => {
      const all = await Promise.all([
        subscribeRaw(session, camImage(realm), onFrame, 1),
        subscribeLatest(
          session,
          camStatus(realm),
          (msg) => setStatus(msg as CameraStatus),
          8,
        ),
        watchAlive(session, camAlive(realm), setAlive),
      ]);
      if (disposed) for (const unsub of all) unsub();
      else unsubs.push(...all);
    })();
    return () => {
      disposed = true;
      for (const unsub of unsubs) unsub();
      if (urlRef.current !== null) {
        URL.revokeObjectURL(urlRef.current);
        urlRef.current = null;
      }
    };
  }, [session, realm]);

  useEffect(() => {
    const timer = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const send = async (action: string, payload: unknown, timeoutMs = 5000) => {
    if (session === null) return;
    setCmdError(null);
    try {
      const reply = (await query(
        session,
        camCmd(realm, action),
        payload,
        timeoutMs,
      )) as Ack | null;
      if (reply === null) setCmdError(`no reply from cmd/${action}`);
      else if (!reply.ok) setCmdError(reply.error ?? `cmd/${action} failed`);
    } catch (e) {
      setCmdError(e instanceof Error ? e.message : String(e));
    }
  };

  const grab = async () => {
    if (session === null) return;
    setCmdError(null);
    try {
      // The grabbed frame arrives through the SAME image subscription (the
      // driver publishes every grab) — the reply is only for error display.
      const reply = (await query(
        session,
        camCmd(realm, "grab"),
        { encoding: "jpeg", quality: 95 },
        15000,
      )) as GrabReply | null;
      if (reply === null) setCmdError("no reply from cmd/grab");
      else if (!reply.ok) setCmdError(reply.error ?? "grab failed");
    } catch (e) {
      setCmdError(e instanceof Error ? e.message : String(e));
    }
  };

  const applyConfigure = async () => {
    const payload: Record<string, number> = {};
    if (exposure.trim() !== "") payload.exposure_us = Number(exposure);
    if (gain.trim() !== "") payload.gain_db = Number(gain);
    if (Object.keys(payload).length === 0) return;
    await send("configure", payload);
  };

  const cmdEnabled = commandsEnabled && wsConnected;
  const streaming = status?.streaming === true;

  const ageS =
    frame === null || nowMs === 0
      ? null
      : Number(
          BigInt(nowMs) * 1_000_000n - asBigInt(frame.header.t_capture),
        ) / 1e9;

  return (
    <div className="grid h-full min-h-0 grid-cols-1 gap-2 overflow-y-auto p-2 @min-[560px]:grid-cols-[minmax(0,1fr)_280px]">
      <Card size="sm" className="min-h-0">
        <CardHeader>
          <CardTitle>cam0</CardTitle>
        </CardHeader>
        <CardContent className="flex min-h-0 flex-col gap-2">
          <div className="flex min-h-0 flex-1 items-center justify-center overflow-hidden rounded-md border bg-black/20">
            {frame === null ? (
              <p className="p-8 text-sm text-muted-foreground">
                no stream — start one or grab a frame
              </p>
            ) : frame.url !== null ? (
              <img
                src={frame.url}
                alt={`cam0 frame ${frame.header.seq}`}
                className="max-h-full max-w-full object-contain"
              />
            ) : (
              <p className="p-8 text-sm text-muted-foreground">
                raw stream ({frame.header.encoding} {frame.header.w}×
                {frame.header.h}) — not renderable in browser
              </p>
            )}
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-sm tabular-nums">
            <span>
              <span className="text-muted-foreground">seq</span>{" "}
              {frame?.header.seq ?? "—"}
            </span>
            <span>
              <span className="text-muted-foreground">size</span>{" "}
              {frame === null ? "—" : `${frame.header.w}×${frame.header.h}`}
            </span>
            <span>
              <span className="text-muted-foreground">encoding</span>{" "}
              {frame?.header.encoding ?? "—"}
            </span>
            <span>
              <span className="text-muted-foreground">age</span>{" "}
              {ageS === null ? "—" : `${ageS.toFixed(1)} s`}
            </span>
          </div>
        </CardContent>
      </Card>

      <Card size="sm">
        <CardHeader>
          <CardTitle>Camera</CardTitle>
          <CardAction>
            <Badge
              variant={alive ? "secondary" : "destructive"}
              className={alive ? "bg-ok/20 text-ok" : undefined}
            >
              {alive ? "ALIVE" : "DOWN"}
            </Badge>
          </CardAction>
        </CardHeader>
        <CardContent className="space-y-3">
          <dl className={KV_CLASS}>
            <dt className="text-muted-foreground">connected</dt>
            <dd>{status === null ? "—" : String(status.connected)}</dd>
            <dt className="text-muted-foreground">streaming</dt>
            <dd>{status === null ? "—" : String(status.streaming)}</dd>
            <dt className="text-muted-foreground">rate</dt>
            <dd>
              {status === null ? "—" : `${status.achieved_rate_hz.toFixed(1)} Hz`}
            </dd>
            <dt className="text-muted-foreground">exposure</dt>
            <dd>
              {status?.exposure_us == null
                ? "—"
                : `${status.exposure_us.toFixed(0)} µs`}
            </dd>
            <dt className="text-muted-foreground">gain</dt>
            <dd>
              {status?.gain_db == null ? "—" : `${status.gain_db.toFixed(1)} dB`}
            </dd>
            <dt className="text-muted-foreground">error</dt>
            <dd className={status?.error ? "text-destructive" : undefined}>
              {status?.error ?? "none"}
            </dd>
          </dl>

          <h3 className="pt-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Browser producer
          </h3>
          <dl className={KV_CLASS}>
            <dt className="text-muted-foreground">mode</dt>
            <dd>{producer.mode}</dd>
            <dt className="text-muted-foreground">lease</dt>
            <dd>
              {producer.ownsLease
                ? `owned · epoch ${producer.owner?.epoch}`
                : producer.owner === null
                  ? "available"
                  : `held by ${producer.owner.user}`}
            </dd>
            <dt className="text-muted-foreground">render rate</dt>
            <dd>{producer.achievedRateHz.toFixed(1)} Hz</dd>
          </dl>
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              className="cmd flex-1"
              disabled={producer.mode !== "stopped"}
              onClick={producer.start}
            >
              Start producer
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="cmd flex-1"
              disabled={producer.mode === "stopped"}
              onClick={
                producer.mode === "pip"
                  ? producer.dock
                  : () => void producer.popOut()
              }
            >
              {producer.mode === "pip" ? "Back to tab" : "Always on top"}
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="cmd flex-1"
              disabled={producer.mode === "stopped"}
              onClick={producer.stop}
            >
              Stop producer
            </Button>
          </div>
          {producer.error !== null && (
            <p className="text-sm text-destructive">{producer.error}</p>
          )}

          <h3 className="pt-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Stream
          </h3>
          <div className="grid grid-cols-3 gap-1">
            <Select value={rate} onValueChange={setRate} disabled={!cmdEnabled}>
              <SelectTrigger size="sm" className="cmd" title="rate (Hz)">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {RATE_OPTIONS.map((v) => (
                  <SelectItem key={v} value={v}>
                    {v} Hz
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={scale} onValueChange={setScale} disabled={!cmdEnabled}>
              <SelectTrigger size="sm" className="cmd" title="scale">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {SCALE_OPTIONS.map((v) => (
                  <SelectItem key={v} value={v}>
                    ×{v}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={quality}
              onValueChange={setQuality}
              disabled={!cmdEnabled}
            >
              <SelectTrigger size="sm" className="cmd" title="jpeg quality">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {QUALITY_OPTIONS.map((v) => (
                  <SelectItem key={v} value={v}>
                    q{v}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              className="cmd flex-1"
              disabled={!cmdEnabled}
              onClick={() =>
                void send("stream_start", {
                  rate_hz: Number(rate),
                  scale: Number(scale),
                  quality: Number(quality),
                  encoding: "jpeg",
                })
              }
            >
              Start stream
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="cmd flex-1"
              disabled={!cmdEnabled}
              onClick={() => void send("stream_stop", {})}
            >
              Stop
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="cmd flex-1"
              disabled={!cmdEnabled || streaming}
              title={streaming ? "stop the stream first" : "full-res jpeg grab"}
              onClick={() => void grab()}
            >
              Grab
            </Button>
          </div>

          <h3 className="pt-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Configure
          </h3>
          <div className="grid grid-cols-2 gap-1">
            <Input
              type="number"
              placeholder="exposure µs"
              className="cmd"
              value={exposure}
              onChange={(e) => setExposure(e.target.value)}
              disabled={!cmdEnabled}
            />
            <Input
              type="number"
              placeholder="gain dB"
              className="cmd"
              value={gain}
              onChange={(e) => setGain(e.target.value)}
              disabled={!cmdEnabled}
            />
          </div>
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              className="cmd flex-1"
              disabled={!cmdEnabled || (exposure.trim() === "" && gain.trim() === "")}
              onClick={() => void applyConfigure()}
            >
              Apply
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="cmd flex-1"
              disabled={!cmdEnabled}
              onClick={() => void send("configure", { auto_exposure: true })}
            >
              Auto exp
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="cmd flex-1"
              disabled={!cmdEnabled}
              onClick={() => void send("configure", { auto_gain: true })}
            >
              Auto gain
            </Button>
          </div>
          {cmdError !== null && (
            <p className="text-sm text-destructive">{cmdError}</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
