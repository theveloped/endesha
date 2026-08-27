// Device tree (top-right of the 3D scene): the cell's logical devices with a
// per-device source picker (live/sim/replay/off). Driven by the supervisor's
// `devices` publication; switching sends cmd/set_source (a cold switch). A
// confirm dialog guards switching a device to `live` (real hardware).
import { useEffect, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { cn } from "@/lib/utils";
import { setDeviceSource } from "../lib/actions";
import { query, subscribeLatest, watchAlive, type Unsubscribe } from "../lib/bus";
import { alive, camAlive, dioAlive, supervisorDevices, tagsAlive, washerAlive } from "../lib/config";
import type { DeviceEntry, DevicesList } from "../lib/messages";

function deviceAliveKey(realm: string, d: DeviceEntry): string {
  if (d.contract === "camera2d") return camAlive(realm, d.id);
  if (d.contract === "dio") return dioAlive(realm, d.id);
  if (d.contract === "tags") return tagsAlive(realm, d.id);
  if (d.contract === "washer") return washerAlive(realm, d.id);
  return alive(realm, d.id);
}

/** Declared modes + `off`, de-duplicated, in a stable order. */
function modesFor(d: DeviceEntry): string[] {
  const order = ["live", "sim", "replay", "off"];
  const set = new Set<string>([...d.sources.map((s) => s.mode), "off"]);
  const known = order.filter((m) => set.has(m));
  const extra = [...set].filter((m) => !order.includes(m));
  return [...known, ...extra];
}

export default function DeviceTree({
  session,
  realm,
  commandsEnabled,
  devices: suppliedDevices,
}: {
  session: Session | null;
  realm: string;
  commandsEnabled: boolean;
  devices?: DeviceEntry[];
}) {
  const [deviceSample, setDeviceSample] = useState<{
    session: Session | null;
    realm: string;
    devices: DeviceEntry[];
  }>({ session: null, realm: "", devices: [] });
  const [aliveSample, setAliveSample] = useState<{
    session: Session | null;
    realm: string;
    map: Record<string, boolean>;
  }>({ session: null, realm: "", map: {} });
  const devices =
    suppliedDevices ??
    (deviceSample.session === session && deviceSample.realm === realm
      ? deviceSample.devices
      : []);
  const aliveMap =
    aliveSample.session === session && aliveSample.realm === realm
      ? aliveSample.map
      : {};
  const [pending, setPending] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<{ id: string; mode: string } | null>(null);

  // Subscribe + initial query the devices inventory.
  useEffect(() => {
    if (session === null || suppliedDevices !== undefined) return;
    let disposed = false;
    const unsubs: Unsubscribe[] = [];
    void (async () => {
      const u = await subscribeLatest(
        session,
        supervisorDevices(realm),
        (m) =>
          setDeviceSample({
            session,
            realm,
            devices: (m as DevicesList).devices ?? [],
          }),
        4,
      );
      if (disposed) u();
      else unsubs.push(u);
      const cur = await query(session, supervisorDevices(realm), {});
      if (!disposed && cur !== null) {
        setDeviceSample({
          session,
          realm,
          devices: (cur as DevicesList).devices ?? [],
        });
      }
    })();
    return () => {
      disposed = true;
      for (const u of unsubs) u();
    };
  }, [session, realm, suppliedDevices]);

  // Watch each device's own liveliness token (re-subscribe when the set changes).
  const ids = devices.map((d) => d.id).join(",");
  useEffect(() => {
    if (session === null) return;
    let disposed = false;
    const unsubs: Unsubscribe[] = [];
    void (async () => {
      for (const d of devices) {
        const u = await watchAlive(session, deviceAliveKey(realm, d), (alive) =>
          setAliveSample((previous) => ({
            session,
            realm,
            map:
              previous.session === session && previous.realm === realm
                ? { ...previous.map, [d.id]: alive }
                : { [d.id]: alive },
          })),
        );
        if (disposed) u();
        else unsubs.push(u);
      }
    })();
    return () => {
      disposed = true;
      for (const u of unsubs) u();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session, realm, ids]);

  const doSwitch = async (id: string, mode: string) => {
    if (session === null) return;
    setPending(id);
    try {
      const reply = await setDeviceSource(session, realm, id, mode);
      if (!reply.ok) console.error("set_source failed:", reply.error);
    } catch (e) {
      console.error("set_source error:", e);
    } finally {
      setPending(null);
    }
  };

  const onPick = (d: DeviceEntry, mode: string) => {
    if (mode === d.active) return;
    if (mode === "live") setConfirm({ id: d.id, mode }); // guard real hardware
    else void doSwitch(d.id, mode);
  };

  if (devices.length === 0) return null; // no supervisor in this namespace

  return (
    <div className="pointer-events-auto w-full rounded-lg bg-zinc-950/2.5 p-2 text-xs ring-1 ring-zinc-950/5 dark:bg-white/5 dark:ring-white/10">
      <div className="mb-1 font-semibold tracking-wide text-muted-foreground">
        DEVICES
      </div>
      <ul className="space-y-1">
        {devices.map((d) => {
          const external =
            d.sources.find((s) => s.mode === d.active)?.launch === "external";
          return (
            <li key={d.id} className="flex items-center gap-1.5">
              <span
                title={aliveMap[d.id] ? "alive" : "down"}
                className={cn(
                  "inline-block size-2 shrink-0 rounded-full",
                  aliveMap[d.id] ? "bg-ok" : "bg-muted-foreground/40",
                )}
              />
              <span className="font-medium">{d.id}</span>
              <span className="text-muted-foreground">{d.contract}</span>
              {d.provided_by !== undefined ? (
                <span
                  className="ml-auto text-muted-foreground"
                  title={`served by ${d.provided_by}'s provider process; follows its source`}
                >
                  {d.active ?? "off"} · via {d.provided_by}
                </span>
              ) : (
                <select
                  className="ml-auto rounded border border-border bg-background px-1 py-0.5 text-xs disabled:opacity-50"
                  value={d.active ?? "off"}
                  disabled={!commandsEnabled || pending === d.id}
                  onChange={(e) => onPick(d, e.target.value)}
                >
                  {modesFor(d).map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
              )}
              {external && (
                <span
                  title="served by an external process (e.g. the headless camera) — the supervisor does not start it"
                  className="text-[10px] uppercase text-amber-400"
                >
                  ext
                </span>
              )}
            </li>
          );
        })}
      </ul>

      <AlertDialog
        open={confirm !== null}
        onOpenChange={(o) => {
          if (!o) setConfirm(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Switch {confirm?.id} to LIVE?</AlertDialogTitle>
            <AlertDialogDescription>
              This drives real hardware and briefly interrupts the device.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                if (confirm !== null) void doSwitch(confirm.id, confirm.mode);
                setConfirm(null);
              }}
            >
              Switch to LIVE
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
