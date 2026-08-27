import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { Session } from "@eclipse-zenoh/zenoh-ts";
import { SimCameraRenderer } from "./SimCameraRenderer";
import { subscribeConfigList, subscribeLatest, type Unsubscribe } from "../lib/bus";
import type { BrowserProducerState } from "../lib/camera2d/producer";
import {
  configFramesGlob,
  configSceneGlob,
  stateFlange,
  stateJoints,
} from "../lib/config";
import { BASE_FRAME, frameWorldMatrix } from "../lib/framemath";
import type {
  FlangeState,
  FrameDef,
  Intrinsics,
  JointState,
  SceneObject,
} from "../lib/messages";

interface BrowserCameraProducerProps {
  session: Session | null;
  realm: string | null;
  producer: BrowserProducerState;
}

export function BrowserCameraProducer({
  session,
  realm,
  producer,
}: BrowserCameraProducerProps) {
  const [frames, setFrames] = useState<{ name: string; def: FrameDef }[]>([]);
  const [scene, setScene] = useState<{ name: string; obj: SceneObject }[]>([]);
  const flangeRef = useRef<FlangeState | null>(null);
  const jointsRef = useRef<JointState | null>(null);

  useEffect(() => {
    if (session === null || realm === null || producer.mode === "stopped") return;
    let disposed = false;
    const unsubs: Unsubscribe[] = [];
    void (async () => {
      const next = await Promise.all([
        subscribeConfigList(session, configFramesGlob(), "config/frames/", (items) =>
          setFrames(items.map((item) => ({ name: item.name, def: item.value as FrameDef }))),
        ),
        subscribeConfigList(session, configSceneGlob(), "config/scene/", (items) =>
          setScene(items.map((item) => ({ name: item.name, obj: item.value as SceneObject }))),
        ),
        subscribeLatest(session, stateFlange(realm), (message) => {
          flangeRef.current = message as FlangeState;
        }),
        subscribeLatest(session, stateJoints(realm), (message) => {
          jointsRef.current = message as JointState;
        }),
      ]);
      if (disposed) next.forEach((unsubscribe) => unsubscribe());
      else unsubs.push(...next);
    })();
    return () => {
      disposed = true;
      unsubs.forEach((unsubscribe) => unsubscribe());
    };
  }, [producer.mode, realm, session]);

  const baseMatrix = useMemo(() => {
    const map = new Map(frames.map((frame) => [frame.name, frame.def]));
    return frameWorldMatrix(map, BASE_FRAME);
  }, [frames]);

  const demand = producer.demand;
  const target = producer.renderTarget;
  if (producer.mode === "stopped" || demand === null || target === null) return null;
  const { w, h, fx, fy } = demand.intrinsics;
  const intrinsics: Intrinsics = {
    w,
    h,
    fx,
    fy,
    cx: (w - 1) / 2,
    cy: (h - 1) / 2,
  };
  const scale = demand.stream?.scale ?? 0.25;
  const renderer = (
    <div
      style={
        producer.mode === "pip"
          ? { width: "100vw", height: "100vh", display: "grid", placeItems: "center" }
          : {
              position: "fixed",
              right: 16,
              bottom: 16,
              zIndex: 100,
              border: "1px solid #3f3f46",
              boxShadow: "0 12px 32px rgb(0 0 0 / 35%)",
            }
      }
    >
      <SimCameraRenderer
        intrinsics={intrinsics}
        flangeRef={flangeRef}
        mountXyz={demand.mount_xyz}
        mountRpyDeg={demand.mount_rpy_deg}
        baseMatrix={baseMatrix}
        onGrabReady={producer.setGrab}
        frames={frames}
        scene={scene}
        jointsRef={jointsRef}
        renderScale={scale}
      />
    </div>
  );
  return createPortal(renderer, target);
}
