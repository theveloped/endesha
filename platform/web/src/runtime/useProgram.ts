// Live view of the cell's program unit: catalog, state, transition log, runner
// liveliness. Used by the Programs tool and the operator HMI.
import { useEffect, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { query, subscribeLatest, watchAlive, type Unsubscribe } from "../lib/bus";
import {
  programAlive,
  programLog,
  programState,
  programTransitions,
  programsCatalog,
} from "../lib/config";
import type { ProgramCatalog, ProgramLogLine, ProgramState, TransitionEvent } from "../lib/messages";

const TRANSITION_LOG_MAX = 200;
const LOG_MAX = 300;

export interface ProgramView {
  alive: boolean;
  catalog: ProgramCatalog | null;
  state: ProgramState | null;
  transitions: TransitionEvent[];
  log: ProgramLogLine[];
  refreshCatalog: () => void;
}

export function useProgram(session: Session | null, realm: string | null): ProgramView {
  const [alive, setAlive] = useState(false);
  const [catalog, setCatalog] = useState<ProgramCatalog | null>(null);
  const [state, setState] = useState<ProgramState | null>(null);
  const [transitions, setTransitions] = useState<TransitionEvent[]>([]);
  const [log, setLog] = useState<ProgramLogLine[]>([]);
  const [catalogNonce, setCatalogNonce] = useState(0);

  useEffect(() => {
    setAlive(false);
    setCatalog(null);
    setState(null);
    setTransitions([]);
    setLog([]);
    if (session === null || realm === null) return;
    const subs: Unsubscribe[] = [];
    let disposed = false;
    void (async () => {
      const next = await Promise.all([
        watchAlive(session, programAlive(realm), setAlive),
        subscribeLatest(session, programState(realm), (m) => setState(m as ProgramState), 4),
        subscribeLatest(session, programsCatalog(realm), (m) => setCatalog(m as ProgramCatalog), 2),
        subscribeLatest(
          session,
          programTransitions(realm),
          (m) =>
            setTransitions((current) => {
              const list = [...current, m as TransitionEvent];
              return list.length > TRANSITION_LOG_MAX ? list.slice(-TRANSITION_LOG_MAX) : list;
            }),
          64,
        ),
        subscribeLatest(
          session,
          programLog(realm),
          (m) =>
            setLog((current) => {
              const list = [...current, m as ProgramLogLine];
              return list.length > LOG_MAX ? list.slice(-LOG_MAX) : list;
            }),
          64,
        ),
      ]);
      if (disposed) next.forEach((u) => u());
      else subs.push(...next);
      // Late joiner: pull the current values once.
      const [st, cat, lg] = await Promise.all([
        query(session, programState(realm), {}),
        query(session, programsCatalog(realm), {}),
        query(session, programLog(realm), {}),
      ]);
      if (disposed) return;
      if (st !== null) setState(st as ProgramState);
      if (cat !== null) setCatalog(cat as ProgramCatalog);
      if (lg !== null) {
        const lines = ((lg as { lines?: ProgramLogLine[] }).lines ?? []) as ProgramLogLine[];
        setLog((current) => (current.length === 0 ? lines.slice(-LOG_MAX) : current));
      }
    })();
    return () => {
      disposed = true;
      subs.forEach((u) => u());
    };
  }, [session, realm]);

  useEffect(() => {
    if (session === null || realm === null || catalogNonce === 0) return;
    void query(session, programsCatalog(realm), {}).then((cat) => {
      if (cat !== null) setCatalog(cat as ProgramCatalog);
    });
  }, [session, realm, catalogNonce]);

  return {
    alive,
    catalog,
    state,
    transitions,
    log,
    refreshCatalog: () => setCatalogNonce((n) => n + 1),
  };
}
