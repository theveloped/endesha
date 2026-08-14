import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type PropsWithChildren,
} from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { BrowserCameraProducer } from "../components/BrowserCameraProducer";
import { acquireControl, releaseControl } from "../lib/actions";
import {
  connect,
  query,
  subscribeLatest,
  watchAlive,
  watchReplaySessions,
  type Unsubscribe,
} from "../lib/bus";
import { useBrowserCameraProducer } from "../lib/camera2d/producer";
import {
  DEFAULT_WS_URL,
  alive,
  realmPrefix,
  stateControlOwner,
  stateFlange,
  stateIo,
  stateJoints,
  stateStatus,
  type Realm,
  supervisorDevices,
} from "../lib/config";
import type {
  ArmStatus,
  ControlOwnerState,
  FlangeState,
  IoState,
  JointState,
  DevicesList,
} from "../lib/messages";
import { RuntimeContext } from "./context";

interface Targeted<T> {
  session: Session | null;
  prefix: string | null;
  value: T;
}


export function RuntimeProvider({ children }: PropsWithChildren) {
  const [url, setUrl] = useState(DEFAULT_WS_URL);
  const [session, setSession] = useState<Session | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);
  const [realm, setRealm] = useState<Realm>({ kind: "cell", replaySession: null });
  const [replaySessions, setReplaySessions] = useState<string[]>([]);
  const [ioSample, setIoSample] = useState<Targeted<IoState | null>>({
    session: null,
    prefix: null,
    value: null,
  });
  const [statusSample, setStatusSample] = useState<Targeted<ArmStatus | null>>({
    session: null,
    prefix: null,
    value: null,
  });
  const [aliveSample, setAliveSample] = useState<Targeted<boolean>>({
    session: null,
    prefix: null,
    value: false,
  });
  const [stale, setStale] = useState(true);
  const [wsClosed, setWsClosed] = useState(false);
  const [ownerSample, setOwnerSample] = useState<Targeted<ControlOwnerState | null>>({
    session: null,
    prefix: null,
    value: null,
  });
  const [devices, setDevices] = useState<DevicesList | null>(null);
  const [clientId] = useState(() => crypto.randomUUID());
  const [user] = useState(() => localStorage.getItem("wf.user") ?? "operator");
  const jointsRef = useRef<JointState | null>(null);
  const jointsCountRef = useRef(0);
  const flangeRef = useRef<FlangeState | null>(null);
  const lastStatusAtRef = useRef(0);
  const prefix = realmPrefix(realm);
  const io =
    ioSample.session === session && ioSample.prefix === prefix
      ? ioSample.value
      : null;
  const status =
    statusSample.session === session && statusSample.prefix === prefix
      ? statusSample.value
      : null;
  const aliveToken =
    aliveSample.session === session && aliveSample.prefix === prefix
      ? aliveSample.value
      : false;
  const controlOwner =
    ownerSample.session === session && ownerSample.prefix === prefix
      ? ownerSample.value
      : null;

  const doConnect = useCallback(async () => {
    setConnecting(true);
    setConnectError(null);
    try {
      if (session !== null) {
        try {
          await session.close();
        } catch {
          // The old session may already be closed.
        }
        setSession(null);
      }
      const next = await connect(url);
      lastStatusAtRef.current = Date.now();
      setWsClosed(false);
      setSession(next);
    } catch (error) {
      setConnectError(error instanceof Error ? error.message : String(error));
    } finally {
      setConnecting(false);
    }
  }, [session, url]);


  useEffect(() => {
    if (session === null || prefix === null) return;
    jointsRef.current = null;
    flangeRef.current = null;
    lastStatusAtRef.current = Date.now();
    const subscriptions: Unsubscribe[] = [];
    let disposed = false;
    void (async () => {
      const next = await Promise.all([
        subscribeLatest(session, stateJoints(prefix), (message) => {
          jointsRef.current = message as JointState;
          jointsCountRef.current += 1;
        }, 1),
        subscribeLatest(session, stateFlange(prefix), (message) => {
          flangeRef.current = message as FlangeState;
        }, 1),
        subscribeLatest(session, stateIo(prefix), (message) => {
          setIoSample({ session, prefix, value: message as IoState });
        }, 8),
        subscribeLatest(session, stateStatus(prefix), (message) => {
          setStatusSample({ session, prefix, value: message as ArmStatus });
          lastStatusAtRef.current = Date.now();
        }, 8),
        watchAlive(session, alive(prefix), (value) => {
          setAliveSample({ session, prefix, value });
        }),
        subscribeLatest(session, stateControlOwner(prefix), (message) => {
          setOwnerSample({
            session,
            prefix,
            value: message as ControlOwnerState,
          });
        }, 4),
      ]);
      if (disposed) next.forEach((unsubscribe) => unsubscribe());
      else subscriptions.push(...next);
    })();
    return () => {
      disposed = true;
      subscriptions.forEach((unsubscribe) => unsubscribe());
    };
  }, [session, prefix]);

  useEffect(() => {
    if (session === null) return;
    let disposed = false;
    let unsubscribe: Unsubscribe | null = null;
    void (async () => {
      const next = await watchReplaySessions(session, (sessions) => {
        setReplaySessions(sessions);
        setRealm((current) =>
          current.kind === "replay" &&
          current.replaySession !== null &&
          !sessions.includes(current.replaySession)
            ? { kind: "replay", replaySession: null }
            : current,
        );
      });
      if (disposed) next();
      else unsubscribe = next;
    })();
    return () => {
      disposed = true;
      unsubscribe?.();
    };
  }, [session]);

  useEffect(() => {
    if (session === null) return;
    const timer = setInterval(() => {
      setStale(Date.now() - lastStatusAtRef.current > 3000);
      setWsClosed(session.isClosed());
    }, 1000);
    return () => clearInterval(timer);
  }, [session]);

  useEffect(() => {
    if (session === null || prefix === null || realm.kind !== "cell") {
      setDevices(null);
      return;
    }
    let disposed = false;
    let unsubscribe: Unsubscribe | null = null;
    void (async () => {
      const next = await subscribeLatest(session, supervisorDevices(prefix), (message) => {
        setDevices(message as DevicesList);
      }, 4);
      if (disposed) {
        next();
        return;
      }
      unsubscribe = next;
      const current = await query(session, supervisorDevices(prefix), {});
      if (!disposed && current !== null) setDevices(current as DevicesList);
    })();
    return () => {
      disposed = true;
      unsubscribe?.();
    };
  }, [prefix, realm.kind, session]);

  const browserCameraActive =
    realm.kind === "cell" &&
    devices?.devices.find((device) => device.id === "cam0")?.active === "browser_sim";
  const cameraProducer = useBrowserCameraProducer(
    session,
    prefix,
    browserCameraActive,
  );

  const wsConnected = session !== null && !wsClosed;
  const driverAlive = wsConnected && !stale && aliveToken;
  const commandsEnabled = realm.kind !== "replay" && driverAlive;
  const safetyActive = status?.estop === true || status?.protective_stop === true;
  const holdsControl = controlOwner?.owner?.client_id === clientId;

  const acquire = useCallback(() => {
    if (session === null || prefix === null) return;
    void acquireControl(session, prefix, clientId, user).catch((error) =>
      console.error("acquire control failed:", error),
    );
  }, [session, prefix, clientId, user]);

  const release = useCallback(() => {
    if (session === null || prefix === null) return;
    void releaseControl(session, prefix, clientId).catch((error) =>
      console.error("release control failed:", error),
    );
  }, [session, prefix, clientId]);

  useEffect(() => {
    if (!holdsControl || session === null || prefix === null) return;
    const timer = setInterval(acquire, 10000);
    return () => clearInterval(timer);
  }, [holdsControl, session, prefix, acquire]);

  return (
    <RuntimeContext.Provider
      value={{
        url,
        setUrl,
        session,
        connecting,
        connectError,
        connect: doConnect,
        realm,
        setRealm,
        prefix,
        replaySessions,
        io,
        status,
        wsConnected,
        driverAlive,
        commandsEnabled,
        safetyActive,
        controlOwner,
        clientId,
        holdsControl,
        acquire,
        release,
        jointsRef,
        jointsCountRef,
        flangeRef,
        cameraProducer,
      }}
    >
      <BrowserCameraProducer session={session} realm={prefix} producer={cameraProducer} />
      {children}
    </RuntimeContext.Provider>
  );
}
