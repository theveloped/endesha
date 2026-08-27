import { useCallback, useEffect, useState } from "react";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { queryAll, subscribeLatest, type Unsubscribe } from "../lib/bus";
import {
  configFramesGlob,
  configPosesGlob,
  configSceneGlob,
  configTcpsGlob,
  supervisorDevices,
} from "../lib/config";
import type {
  DeviceEntry,
  DevicesList,
  FrameDef,
  PoseDef,
  SceneObject,
  TcpDef,
} from "../lib/messages";

export interface NamedFrame {
  name: string;
  def: FrameDef;
}

export interface NamedTcp {
  name: string;
  def: TcpDef;
}

export interface NamedPose {
  name: string;
  def: PoseDef;
}

export interface NamedSceneObject {
  name: string;
  obj: SceneObject;
}

export interface SceneStructure {
  frames: NamedFrame[];
  tcps: NamedTcp[];
  poses: NamedPose[];
  objects: NamedSceneObject[];
  devices: DeviceEntry[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const EMPTY: Omit<SceneStructure, "loading" | "error" | "refresh"> = {
  frames: [],
  tcps: [],
  poses: [],
  objects: [],
  devices: [],
};

export function useSceneStructure(
  session: Session | null,
  realm: string | null,
  revision = 0,
): SceneStructure {
  const [data, setData] = useState(EMPTY);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (session === null) {
      setData(EMPTY);
      return;
    }
    setLoading(true);
    try {
      const [frames, tcps, poses, objects, deviceReply] = await Promise.all([
        queryAll(session, configFramesGlob()),
        queryAll(session, configTcpsGlob()),
        queryAll(session, configPosesGlob()),
        queryAll(session, configSceneGlob()),
        realm === null ? Promise.resolve(null) : queryAll(session, supervisorDevices(realm)),
      ]);
      const devices =
        deviceReply === null || deviceReply.length === 0
          ? []
          : ((deviceReply[0].value as DevicesList).devices ?? []);
      setData({
        frames: frames
          .map((entry) => ({
            name: entry.key.replace(/^config\/frames\//, ""),
            def: entry.value as FrameDef,
          }))
          .sort((a, b) => a.name.localeCompare(b.name)),
        tcps: tcps
          .map((entry) => ({
            name: entry.key.split("/").pop() ?? entry.key,
            def: entry.value as TcpDef,
          }))
          .sort((a, b) => a.name.localeCompare(b.name)),
        poses: poses
          .map((entry) => ({
            name: entry.key.replace(/^config\/poses\//, ""),
            def: entry.value as PoseDef,
          }))
          .sort((a, b) => a.name.localeCompare(b.name)),
        objects: objects
          .map((entry) => ({
            name: entry.key.replace(/^config\/scene\//, ""),
            obj: entry.value as SceneObject,
          }))
          .sort((a, b) => a.name.localeCompare(b.name)),
        devices: [...devices].sort((a, b) => a.id.localeCompare(b.id)),
      });
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : String(reason));
    } finally {
      setLoading(false);
    }
  }, [session, realm]);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => window.clearTimeout(timer);
  }, [refresh, revision]);

  useEffect(() => {
    if (session === null || realm === null) return;
    let disposed = false;
    let unsubscribe: Unsubscribe | null = null;
    void subscribeLatest(
      session,
      supervisorDevices(realm),
      (message) => {
        if (disposed) return;
        setData((previous) => ({
          ...previous,
          devices: [...((message as DevicesList).devices ?? [])].sort((a, b) =>
            a.id.localeCompare(b.id),
          ),
        }));
      },
      4,
    ).then((next) => {
      if (disposed) next();
      else unsubscribe = next;
    });
    return () => {
      disposed = true;
      unsubscribe?.();
    };
  }, [session, realm]);

  return { ...data, loading, error, refresh };
}
