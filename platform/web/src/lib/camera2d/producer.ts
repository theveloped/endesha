import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { encodeWire, type Wire } from "./cbor";
import type { GrabFrame } from "../../components/SimCameraRenderer";
import {
  declareQueryable,
  declareRawPublisher,
  query,
  queryPayload,
  replyBytes,
  subscribeLatest,
  type RawPublisher,
  type Unsubscribe,
} from "../bus";
import {
  camProducerCmd,
  camProducerDemand,
  camProducerIngress,
  camProducerOwner,
  camProducerRender,
} from "../config";
import type {
  ProducerAck,
  ProducerDemand,
  ProducerGrant,
  ProducerOwnerState,
} from "../messages";

export type ProducerMode = "stopped" | "foreground" | "pip";

export interface BrowserProducerState {
  mode: ProducerMode;
  owner: ProducerGrant | null;
  demand: ProducerDemand | null;
  ownsLease: boolean;
  error: string | null;
  achievedRateHz: number;
  renderTarget: HTMLElement | null;
  start: () => void;
  popOut: () => Promise<Window | null>;
  dock: () => void;
  stop: () => void;
  setGrab: (grab: GrabFrame | null) => void;
}

export function useBrowserCameraProducer(
  session: Session | null,
  realm: string | null,
  enabled: boolean,
): BrowserProducerState {
  const [mode, setMode] = useState<ProducerMode>("stopped");
  const [owner, setOwner] = useState<ProducerGrant | null>(null);
  const [demand, setDemand] = useState<ProducerDemand | null>(null);
  const [renderTarget, setRenderTarget] = useState<HTMLElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [achievedRateHz, setAchievedRateHz] = useState(0);
  const clientId = useMemo(() => crypto.randomUUID(), []);
  const user = useMemo(() => localStorage.getItem("wf.user") ?? "operator", []);
  const grantRef = useRef<ProducerGrant | null>(null);
  const demandRef = useRef<ProducerDemand | null>(null);
  const grabRef = useRef<GrabFrame | null>(null);
  const pubRef = useRef<RawPublisher | null>(null);
  const renderUnsubRef = useRef<Unsubscribe | null>(null);
  const pipRef = useRef<Window | null>(null);
  const framesRef = useRef({ count: 0, at: performance.now() });
  const ownsLease = owner?.client_id === clientId;

  const setGrab = useCallback((grab: GrabFrame | null) => {
    grabRef.current = grab;
  }, []);

  const stop = useCallback(() => {
    const pip = pipRef.current;
    pipRef.current = null;
    setRenderTarget(null);
    setMode("stopped");
    const currentSession = session;
    const currentRealm = realm;
    if (currentSession !== null && currentRealm !== null) {
      void query(currentSession, camProducerCmd(currentRealm, "release"), {
        client_id: clientId,
      }).catch(() => undefined);
    }
    pip?.close();
  }, [clientId, realm, session]);

  const start = useCallback(() => {
    if (!enabled) {
      setError("Select the browser_sim camera source before starting a producer");
      return;
    }
    setError(null);
    setRenderTarget(document.body);
    setMode("foreground");
  }, [enabled]);

  const dock = useCallback(() => {
    const pip = pipRef.current;
    if (pip === null) return;
    pipRef.current = null;
    setError(null);
    setRenderTarget(document.body);
    setMode("foreground");
    pip.close();
  }, []);

  const popOut = useCallback(async () => {
    if (!enabled) {
      setError("Select the browser_sim camera source before starting a producer");
      return null;
    }
    if (mode !== "foreground") {
      setError("Start the producer in this tab before opening always-on-top mode");
      return null;
    }
    setError(null);
    const api = window.documentPictureInPicture;
    if (api === undefined) {
      setError("Document Picture-in-Picture is unavailable; continuing in this tab");
      return null;
    }
    let pip: Window;
    try {
      pip = await api.requestWindow({ width: 420, height: 300 });
    } catch (reason) {
      setError(
        reason instanceof Error
          ? `Unable to open always-on-top producer: ${reason.message}`
          : `Unable to open always-on-top producer: ${String(reason)}`,
      );
      return null;
    }
    pip.document.body.style.margin = "0";
    pip.document.body.style.background = "#18181b";
    pip.addEventListener("pagehide", () => {
      if (pipRef.current === pip) {
        pipRef.current = null;
        setRenderTarget(document.body);
        setMode("foreground");
      }
    });
    pipRef.current = pip;
    setRenderTarget(pip.document.body);
    setMode("pip");
    return pip;
  }, [enabled, mode]);

  useEffect(() => {
    grantRef.current = ownsLease ? owner : null;
  }, [owner, ownsLease]);
  useEffect(() => {
    demandRef.current = demand;
  }, [demand]);

  useEffect(() => {
    if (session === null || realm === null) return;
    let disposed = false;
    const unsubs: Unsubscribe[] = [];
    void (async () => {
      const next = await Promise.all([
        subscribeLatest(session, camProducerOwner(realm), (msg) => {
          const state = msg as ProducerOwnerState;
          setOwner(state.owner);
        }, 4),
        subscribeLatest(session, camProducerDemand(realm), (msg) => {
          setDemand(msg as ProducerDemand);
        }, 4),
      ]);
      if (disposed) next.forEach((unsubscribe) => unsubscribe());
      else unsubs.push(...next);
      for (const [key, setter] of [
        [camProducerOwner(realm), (value: unknown) => setOwner((value as ProducerOwnerState).owner)],
        [camProducerDemand(realm), (value: unknown) => setDemand(value as ProducerDemand)],
      ] as const) {
        const value = await query(session, key, {});
        if (!disposed && value !== null) setter(value);
      }
    })();
    return () => {
      disposed = true;
      unsubs.forEach((unsubscribe) => unsubscribe());
    };
  }, [realm, session]);

  useEffect(() => {
    if (!enabled && mode !== "stopped") stop();
  }, [enabled, mode, stop]);

  useEffect(() => {
    if (mode === "stopped" || session === null || realm === null || !enabled) return;
    let disposed = false;
    const acquire = async () => {
      const response = (await query(session, camProducerCmd(realm, "acquire"), {
        client_id: clientId,
        user,
      })) as ProducerAck | null;
      if (disposed) return;
      if (response === null || !response.ok || response.owner === null) {
        setError(response?.error ?? "browser camera provider unavailable");
        setOwner(response?.owner ?? null);
        return;
      }
      setOwner(response.owner);
      setError(null);
    };
    void acquire();
    const timer = setInterval(() => void acquire(), 3000);
    return () => {
      disposed = true;
      clearInterval(timer);
    };
  }, [clientId, enabled, mode, realm, session, user]);

  useEffect(() => {
    if (!ownsLease || session === null || realm === null) return;
    let disposed = false;
    void (async () => {
      const publisher = await declareRawPublisher(session, camProducerIngress(realm), true);
      if (disposed) publisher.undeclare();
      else {
        pubRef.current = publisher;
        renderUnsubRef.current = await declareQueryable(
          session,
          camProducerRender(realm, clientId),
          async (request) => {
            const body = queryPayload(request) as {
              authority_id: string;
              epoch: number;
              spec: { scale: number; quality: number };
            };
            const grant = grantRef.current;
            const grab = grabRef.current;
            if (
              grant === null ||
              grab === null ||
              body.authority_id !== grant.authority_id ||
              body.epoch !== grant.epoch
            ) {
              await replyBytes(request, encodeWire({ ok: false, error: "producer unavailable" }));
              return;
            }
            const frame = await grab(body.spec.scale, body.spec.quality);
            await request.reply(request.keyExpr(), frame.jpeg, {
              attachment: encodeWire(frameAttachment(grant, frame, demandRef.current)),
            });
          },
        );
      }
    })();
    return () => {
      disposed = true;
      pubRef.current?.undeclare();
      pubRef.current = null;
      renderUnsubRef.current?.();
      renderUnsubRef.current = null;
    };
  }, [clientId, ownsLease, realm, session]);

  useEffect(() => {
    const stream = demand?.stream;
    if (!ownsLease || stream === null || stream === undefined) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const period = 1000 / stream.rate_hz;
    const tick = async () => {
      const grant = grantRef.current;
      const grab = grabRef.current;
      const publisher = pubRef.current;
      if (stopped) return;
      if (grant === null || grab === null || publisher === null) {
        timer = setTimeout(() => void tick(), 100);
        return;
      }
      const started = performance.now();
      try {
        const frame = await grab(stream.scale, stream.quality);
        publisher.put(frame.jpeg, encodeWire(frameAttachment(grant, frame, demandRef.current)));
        framesRef.current.count += 1;
        const elapsed = performance.now() - framesRef.current.at;
        if (elapsed >= 1000) {
          setAchievedRateHz((framesRef.current.count * 1000) / elapsed);
          framesRef.current = { count: 0, at: performance.now() };
        }
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : String(reason));
      }
      if (!stopped) timer = setTimeout(() => void tick(), Math.max(0, period - (performance.now() - started)));
    };
    void tick();
    return () => {
      stopped = true;
      clearTimeout(timer);
      setAchievedRateHz(0);
    };
  }, [demand, ownsLease]);

  return {
    mode,
    owner,
    demand,
    ownsLease,
    error,
    renderTarget,
    achievedRateHz,
    start,
    popOut,
    dock,
    stop,
    setGrab,
  };
}

function frameAttachment(
  grant: ProducerGrant,
  frame: { w: number; h: number; pose: unknown },
  demand: ProducerDemand | null,
): Wire {
  return {
    client_id: grant.client_id,
    authority_id: grant.authority_id,
    epoch: grant.epoch,
    captured_at: BigInt(Date.now()) * 1_000_000n,
    w: frame.w,
    h: frame.h,
    encoding: "jpeg",
    exposure_us: demand?.exposure_us ?? 10000,
    gain_db: demand?.gain_db ?? 0,
    pose: frame.pose as Wire,
  };
}

declare global {
  interface Window {
    documentPictureInPicture?: {
      requestWindow(options?: { width?: number; height?: number }): Promise<Window>;
    };
  }
}
