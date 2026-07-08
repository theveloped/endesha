// App shell (gui-design-spec §2): top bar with CELL/REPLAY switcher, nav rail,
// page workspace, global replay drawer. The operating namespace is the fixed
// "cell" token (live/sim is a per-device source mode, not a realm); identical
// page components render the live cell AND recordings by realm-prefix swap.
// A dropped WebSocket is surfaced via Session.isClosed() on the top-bar dot;
// the 3 s status-staleness rule only feeds the ALIVE badge (driverAlive) —
// a paused replay is NOT a disconnect.
import { useCallback, useEffect, useRef, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import NavRail from "./components/NavRail";
import ReplayDrawer from "./components/ReplayDrawer";
import TopBar from "./components/TopBar";
import CamerasPage from "./pages/CamerasPage";
import FramesPage from "./pages/FramesPage";
import IoPage from "./pages/IoPage";
import OperatePage from "./pages/OperatePage";
import OverviewPage from "./pages/OverviewPage";
import FlowsPage from "./pages/FlowsPage";
import TasksPage from "./pages/TasksPage";
import {
  connect,
  subscribeLatest,
  watchAlive,
  watchReplaySessions,
  type Unsubscribe,
} from "./lib/bus";
import { acquireControl, releaseControl } from "./lib/actions";
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
} from "./lib/config";
import type { PageId } from "./lib/nav";
import type {
  ArmStatus,
  ControlOwnerState,
  FlangeState,
  IoState,
  JointState,
} from "./lib/messages";
import { cn } from "@/lib/utils";

function EmptyReplayHint() {
  return (
    <div className="flex h-full items-center justify-center p-8 text-center text-sm text-muted-foreground">
      no replay session selected — start a replayer (
      <code className="font-mono">
        python -m wf.services.recording.replayer &lt;file&gt;.mcap
      </code>
      ) and pick it below.
    </div>
  );
}

export default function App() {
  const [url, setUrl] = useState(DEFAULT_WS_URL);
  const [session, setSession] = useState<Session | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  const [realm, setRealm] = useState<Realm>({
    kind: "cell",
    replaySession: null,
  });
  const [page, setPage] = useState<PageId>("overview");
  const [replaySessions, setReplaySessions] = useState<string[]>([]);

  const jointsRef = useRef<JointState | null>(null);
  const jointsCountRef = useRef(0);
  const flangeRef = useRef<FlangeState | null>(null);
  const lastStatusAtRef = useRef(0);

  const [io, setIo] = useState<IoState | null>(null);
  const [status, setStatus] = useState<ArmStatus | null>(null);
  const [aliveToken, setAliveToken] = useState(false);
  const [stale, setStale] = useState(true);
  const [wsClosed, setWsClosed] = useState(false);

  // Control lease: one stable client id per browser tab; the operator label
  // defaults to a stored name. holdsControl is derived from the published
  // owner state, renewed every 10 s while held (lease TTL is 30 s).
  const [clientId] = useState(() => crypto.randomUUID());
  const [user] = useState(() => localStorage.getItem("wf.user") ?? "operator");
  const [controlOwner, setControlOwner] = useState<ControlOwnerState | null>(null);

  const prefix = realmPrefix(realm);

  const doConnect = async () => {
    setConnecting(true);
    setConnectError(null);
    try {
      if (session !== null) {
        try {
          await session.close();
        } catch {
          // already dead — fine, we are replacing it
        }
        setSession(null);
      }
      const s = await connect(url);
      lastStatusAtRef.current = Date.now(); // 3 s grace before stale
      setWsClosed(false);
      setSession(s);
    } catch (e) {
      setConnectError(e instanceof Error ? e.message : String(e));
    } finally {
      setConnecting(false);
    }
  };

  // Reset stale cross-realm data the moment the subscription target changes
  // (render-phase adjustment, not an effect — avoids a paint of old-realm
  // data and keeps effects subscription-only).
  const [subTarget, setSubTarget] = useState<{
    session: Session | null;
    prefix: string | null;
  }>({ session: null, prefix: null });
  if (subTarget.session !== session || subTarget.prefix !== prefix) {
    setSubTarget({ session, prefix });
    setIo(null);
    setStatus(null);
    setAliveToken(false);
    setControlOwner(null);
  }

  // Realm-keyed state subscriptions: re-point every key on prefix swap.
  useEffect(() => {
    if (session === null || prefix === null) return;
    // Old-realm refs reset here; state resets happen in the render-phase
    // adjustment above.
    jointsRef.current = null;
    flangeRef.current = null;
    lastStatusAtRef.current = Date.now();
    const unsubs: Unsubscribe[] = [];
    let disposed = false;
    void (async () => {
      const all = await Promise.all([
        subscribeLatest(
          session,
          stateJoints(prefix),
          (msg) => {
            jointsRef.current = msg as JointState;
            jointsCountRef.current += 1;
          },
          1,
        ),
        subscribeLatest(
          session,
          stateFlange(prefix),
          (msg) => {
            flangeRef.current = msg as FlangeState;
          },
          1,
        ),
        subscribeLatest(session, stateIo(prefix), (msg) => setIo(msg as IoState), 8),
        subscribeLatest(
          session,
          stateStatus(prefix),
          (msg) => {
            setStatus(msg as ArmStatus);
            lastStatusAtRef.current = Date.now();
          },
          8,
        ),
        watchAlive(session, alive(prefix), setAliveToken),
        subscribeLatest(
          session,
          stateControlOwner(prefix),
          (msg) => setControlOwner(msg as ControlOwnerState),
          4,
        ),
      ]);
      if (disposed) for (const unsub of all) unsub();
      else unsubs.push(...all);
    })();
    return () => {
      disposed = true;
      for (const unsub of unsubs) unsub();
    };
  }, [session, prefix]);

  // Replay session discovery via liveliness on replay/*/*/*/alive. A
  // replayer killed mid-view drops out of the list -> clear the picked
  // session so the workspace shows the empty-replay hint.
  useEffect(() => {
    if (session === null) return;
    let disposed = false;
    let unsub: Unsubscribe | null = null;
    void (async () => {
      const u = await watchReplaySessions(session, (sids) => {
        setReplaySessions(sids);
        setRealm((r) =>
          r.kind === "replay" &&
          r.replaySession !== null &&
          !sids.includes(r.replaySession)
            ? { kind: "replay", replaySession: null }
            : r,
        );
      });
      if (disposed) u();
      else unsub = u;
    })();
    return () => {
      disposed = true;
      if (unsub !== null) unsub();
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

  const wsConnected = session !== null && !wsClosed;
  const driverAlive = wsConnected && !stale && aliveToken;
  const commandsEnabled = realm.kind !== "replay";
  const safetyActive =
    status?.estop === true || status?.protective_stop === true;

  const holdsControl =
    controlOwner?.owner != null &&
    controlOwner.owner.client_id === clientId;

  const acquire = useCallback(() => {
    if (session === null || prefix === null) return;
    void acquireControl(session, prefix, clientId, user).catch((e) =>
      console.error("acquire control failed:", e),
    );
  }, [session, prefix, clientId, user]);

  const release = useCallback(() => {
    if (session === null || prefix === null) return;
    void releaseControl(session, prefix, clientId).catch((e) =>
      console.error("release control failed:", e),
    );
  }, [session, prefix, clientId]);

  // Renew the 30 s lease every 10 s while we hold it.
  useEffect(() => {
    if (!holdsControl || session === null || prefix === null) return;
    const timer = setInterval(() => acquire(), 10000);
    return () => clearInterval(timer);
  }, [holdsControl, session, prefix, acquire]);

  return (
    <div
      className={cn(
        "grid h-full grid-rows-[auto_3px_1fr_auto] grid-cols-[48px_1fr]",
        safetyActive && "safety-active",
      )}
      data-realm={realm.kind}
    >
      <TopBar
        realm={realm}
        onRealmChange={setRealm}
        wsConnected={wsConnected}
        status={status}
        replaySessions={replaySessions}
        url={url}
        onUrlChange={setUrl}
        onConnect={() => void doConnect()}
        connecting={connecting}
        connectError={connectError}
        controlOwner={controlOwner}
        holdsControl={holdsControl}
        commandsEnabled={commandsEnabled}
        driverAlive={driverAlive}
        onAcquire={acquire}
        onRelease={release}
      />
      <div className="col-span-2 h-[3px] bg-[var(--tint)]" />
      <NavRail page={page} onPage={setPage} />
      <main className="workspace min-h-0 overflow-hidden">
        {prefix === null ? (
          <EmptyReplayHint />
        ) : page === "io" ? (
          <IoPage
            session={session}
            realm={prefix}
            io={io}
            wsConnected={wsConnected}
            commandsEnabled={commandsEnabled}
          />
        ) : page === "cameras" ? (
          <CamerasPage
            key={prefix}
            session={session}
            realm={prefix}
            wsConnected={wsConnected}
            commandsEnabled={commandsEnabled}
          />
        ) : page === "frames" ? (
          <FramesPage
            session={session}
            jointsRef={jointsRef}
            flangeRef={flangeRef}
          />
        ) : page === "operate" ? (
          <OperatePage
            session={session}
            realm={prefix}
            clientId={clientId}
            holdsControl={holdsControl}
            ownerUser={controlOwner?.owner?.user ?? null}
            onAcquire={acquire}
            status={status}
            jointsRef={jointsRef}
            driverAlive={driverAlive}
            commandsEnabled={commandsEnabled}
          />
        ) : page === "flows" ? (
          <FlowsPage
            key={prefix}
            session={session}
            realm={prefix}
            wsConnected={wsConnected}
            commandsEnabled={commandsEnabled}
          />
        ) : page === "tasks" ? (
          <TasksPage
            key={prefix}
            session={session}
            realm={prefix}
            wsConnected={wsConnected}
            commandsEnabled={commandsEnabled}
          />
        ) : (
          <OverviewPage
            session={session}
            realm={prefix}
            jointsRef={jointsRef}
            jointsCountRef={jointsCountRef}
            flangeRef={flangeRef}
            status={status}
            driverAlive={driverAlive}
            commandsEnabled={commandsEnabled}
            clientId={clientId}
            holdsControl={holdsControl}
          />
        )}
      </main>
      {realm.kind === "replay" && (
        <ReplayDrawer
          key={realm.replaySession ?? ""}
          session={session}
          sid={realm.replaySession}
          sessions={replaySessions}
          onPickSession={(sid) => setRealm({ kind: "replay", replaySession: sid })}
        />
      )}
    </div>
  );
}
