// Driver status, measured UI joints receive rate (the §9 "full UI rate"
// evidence), flange pose, and the liveliness badge.
import { useEffect, useRef, useState, type RefObject } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ArmStatus, FlangeState } from "../lib/messages";

const KV_CLASS =
  "grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5 font-mono text-sm tabular-nums";

interface StatusPanelProps {
  status: ArmStatus | null;
  /** Liveliness token present AND status not stale (> 3 s without ArmStatus). */
  driverAlive: boolean;
  /** Monotonic count of joints samples received; Hz is derived once per second. */
  jointsCountRef: RefObject<number>;
  flangeRef: RefObject<FlangeState | null>;
  /** Re-arm: unlock a protective stop (stop-induced or manual). */
  onClearProtectiveStop: () => Promise<void>;
}

export default function StatusPanel({
  status,
  driverAlive,
  jointsCountRef,
  flangeRef,
  onClearProtectiveStop,
}: StatusPanelProps) {
  const [jointsHz, setJointsHz] = useState(0);
  const [flange, setFlange] = useState<FlangeState | null>(null);
  const [clearing, setClearing] = useState(false);
  const [clearError, setClearError] = useState<string | null>(null);
  const lastCount = useRef(0);

  const clear = async () => {
    setClearing(true);
    setClearError(null);
    try {
      await onClearProtectiveStop();
    } catch (e) {
      setClearError(e instanceof Error ? e.message : String(e));
    } finally {
      setClearing(false);
    }
  };

  useEffect(() => {
    const hzTimer = setInterval(() => {
      const count = jointsCountRef.current;
      setJointsHz(count - lastCount.current);
      lastCount.current = count;
    }, 1000);
    const flangeTimer = setInterval(() => setFlange(flangeRef.current), 250);
    return () => {
      clearInterval(hzTimer);
      clearInterval(flangeTimer);
    };
  }, [jointsCountRef, flangeRef]);

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle>Status</CardTitle>
        <CardAction>
          <Badge
            variant={driverAlive ? "secondary" : "destructive"}
            className={driverAlive ? "bg-ok/20 text-ok" : undefined}
          >
            {driverAlive ? "ALIVE" : "DOWN"}
          </Badge>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-2">
        <dl className={KV_CLASS}>
          <dt className="text-muted-foreground">mode</dt>
          <dd>{status?.mode ?? "—"}</dd>
          <dt className="text-muted-foreground">servo_on</dt>
          <dd>{status === null ? "—" : String(status.servo_on)}</dd>
          <dt className="text-muted-foreground">estop</dt>
          <dd>{status === null ? "—" : String(status.estop)}</dd>
          <dt className="text-muted-foreground">protective_stop</dt>
          <dd
            className={status?.protective_stop ? "text-destructive" : undefined}
          >
            {status === null ? "—" : String(status.protective_stop)}
          </dd>
          <dt className="text-muted-foreground">speed_scale</dt>
          <dd>{status?.speed_scale ?? "—"}</dd>
          <dt className="text-muted-foreground">state_rate_hz</dt>
          <dd>{status === null ? "—" : status.state_rate_hz.toFixed(1)}</dd>
          <dt className="text-muted-foreground">error</dt>
          <dd>{status?.error ?? "none"}</dd>
          <dt className="text-muted-foreground">joints UI rate</dt>
          <dd>{jointsHz} Hz</dd>
        </dl>
        {status?.protective_stop === true && (
          <Button
            variant="outline"
            className="cmd"
            disabled={clearing}
            onClick={() => void clear()}
          >
            {clearing ? "Clearing…" : "Clear protective stop"}
          </Button>
        )}
        {clearError !== null && (
          <p className="text-sm text-destructive">{clearError}</p>
        )}
        <h3 className="pt-1 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Flange (base frame)
        </h3>
        {flange === null ? (
          <p className="text-sm text-muted-foreground">no flange sample</p>
        ) : (
          <dl className={KV_CLASS}>
            <dt className="text-muted-foreground">xyz</dt>
            <dd>{flange.pose.xyz.map((v) => v.toFixed(4)).join(", ")}</dd>
            <dt className="text-muted-foreground">quat</dt>
            <dd>{flange.pose.quat.map((v) => v.toFixed(3)).join(", ")}</dd>
          </dl>
        )}
      </CardContent>
    </Card>
  );
}
