// Node positions of a program's graph view, live from the config store
// (config/programs/<name>/layout), with a save helper.
import { useCallback, useEffect, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import type { GraphLayout } from "../components/ProgramGraph";
import { configSet } from "../lib/actions";
import { query, subscribeLatest, type Unsubscribe } from "../lib/bus";
import { configProgramLayout } from "../lib/config";

/** Node positions of a program's graph view, live from the config store. */
export function useProgramLayout(session: Session | null, programName: string | null) {
  const [layout, setLayout] = useState<GraphLayout | null>(null);
  useEffect(() => {
    if (session === null || programName === null) return;
    const key = configProgramLayout(programName);
    let disposed = false;
    let unsub: Unsubscribe | null = null;
    const apply = (m: unknown) => {
      const v = m as { positions?: Record<string, [number, number]> } | null;
      setLayout(v && v.positions && Object.keys(v).length > 0 ? { positions: v.positions } : null);
    };
    void (async () => {
      const next = await subscribeLatest(session, key, apply, 4);
      if (disposed) {
        next();
        return;
      }
      unsub = next;
      const current = await query(session, key, {});
      if (!disposed && current !== null) apply(current);
    })();
    return () => {
      disposed = true;
      unsub?.();
      setLayout(null);
    };
  }, [session, programName]);
  const save = useCallback(
    async (next: GraphLayout) => {
      if (session === null || programName === null) return;
      setLayout(next);
      await configSet(session, configProgramLayout(programName), next);
    },
    [session, programName],
  );
  return { layout, save };
}

