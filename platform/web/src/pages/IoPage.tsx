// IO page (spec §6, single `arm r1 onboard` source — no device tabs until a
// second dio device exists): DO toggle grid | DI lamp grid, analog readouts
// below. No optimistic update: lamps render the state stream, never the
// click — a failed write is visible as a toggle that snaps back. Analog is
// read-only (no cmd/set_ao in the arm contract). History strips are a later
// phase (need sample retention the UI doesn't have yet).
import { useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { setDo } from "../lib/actions";
import type { IoState } from "../lib/messages";

const PINS = Array.from({ length: 16 }, (_, i) => i);

interface IoPageProps {
  session: Session | null;
  realm: string;
  io: IoState | null;
  wsConnected: boolean;
  commandsEnabled: boolean;
}

export default function IoPage({
  session,
  realm,
  io,
  wsConnected,
  commandsEnabled,
}: IoPageProps) {
  const [error, setError] = useState<string | null>(null);

  const toggle = async (pin: number, current: boolean) => {
    if (session === null) return;
    setError(null);
    try {
      const ack = await setDo(session, realm, pin, !current);
      if (!ack.ok) setError(ack.error ?? "set_do failed");
    } catch (e) {
      setError(String(e));
    }
  };

  const doEnabled = wsConnected && commandsEnabled && io !== null;

  return (
    <div className="grid h-full min-h-0 grid-rows-[1fr_auto] gap-2 overflow-y-auto p-2">
      <div className="grid grid-cols-2 gap-2">
        <Card size="sm">
          <CardHeader>
            <CardTitle>Digital out</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-8 gap-1">
              {PINS.map((pin) => {
                const on = io !== null && (io.do & (1 << pin)) !== 0;
                return (
                  <Button
                    key={pin}
                    variant="outline"
                    size="sm"
                    className={cn(
                      "cmd font-mono tabular-nums",
                      on && "border-ok bg-ok/20 text-ok",
                    )}
                    disabled={!doEnabled}
                    onClick={() => void toggle(pin, on)}
                    title={`DO ${pin}`}
                  >
                    {pin}
                  </Button>
                );
              })}
            </div>
            {error !== null && (
              <p className="mt-2 text-sm text-destructive">{error}</p>
            )}
          </CardContent>
        </Card>
        <Card size="sm">
          <CardHeader>
            <CardTitle>Digital in</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-8 gap-1">
              {PINS.map((pin) => {
                const on = io !== null && (io.di & (1 << pin)) !== 0;
                return (
                  <span
                    key={pin}
                    title={`DI ${pin}`}
                    className={cn(
                      "flex h-7 items-center justify-center rounded-md border font-mono text-sm tabular-nums",
                      on
                        ? "border-ok bg-ok/20 text-ok"
                        : "border-border text-muted-foreground",
                    )}
                  >
                    {pin}
                  </span>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
      <Card size="sm">
        <CardHeader>
          <CardTitle>Analog</CardTitle>
        </CardHeader>
        <CardContent>
          {io === null ? (
            <p className="text-sm text-muted-foreground">no io sample</p>
          ) : (
            <div className="flex flex-wrap gap-x-6 gap-y-1 font-mono text-sm tabular-nums">
              {io.ai.map((v, i) => (
                <span key={`ai${i}`}>
                  <span className="text-muted-foreground">AI{i}</span>{" "}
                  {v.toFixed(3)}
                </span>
              ))}
              {io.ao.map((v, i) => (
                <span key={`ao${i}`}>
                  <span className="text-muted-foreground">AO{i}</span>{" "}
                  {v.toFixed(3)}
                </span>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
