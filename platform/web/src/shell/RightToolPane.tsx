// The right pane per workspace tool — a route table instead of an if-chain.
import type { ReactNode } from "react";
import DeviceTree from "../components/DeviceTree";
import MotionPanel from "../components/MotionPanel";
import StatusPanel from "../components/StatusPanel";
import { clearProtectiveStop } from "../lib/actions";
import CamerasPage from "../pages/CamerasPage";
import FramesPage from "../pages/FramesPage";
import IoPage from "../pages/IoPage";
import OperatePage from "../pages/OperatePage";
import ProgramsPage from "../pages/ProgramsPage";
import type { RuntimeState } from "../runtime/context";
import type { ProgramView } from "../runtime/useProgram";
import type { ScenePreview } from "../scene/types";
import type { SceneStructure } from "../scene/useSceneStructure";
import type { WorkspaceTool } from "./ToolRibbon";

export interface ToolPaneContext {
  runtime: RuntimeState;
  prefix: string; // non-null realm prefix
  structure: SceneStructure;
  program: ProgramView;
  preview: ScenePreview;
  onPreview: (preview: ScenePreview) => void;
  onConfigurationMutated: () => void;
  onEditProgram: (programName: string | null) => void;
}

const PANES: Record<WorkspaceTool, (ctx: ToolPaneContext) => ReactNode> = {
  overview: ({ runtime, prefix }) => (
    <div className="h-full space-y-2 overflow-y-auto p-2">
      <StatusPanel
        status={runtime.status}
        driverAlive={runtime.driverAlive}
        jointsCountRef={runtime.jointsCountRef}
        flangeRef={runtime.flangeRef}
        onClearProtectiveStop={() => {
          if (runtime.session === null) return Promise.reject(new Error("not connected"));
          return clearProtectiveStop(runtime.session, prefix);
        }}
      />
      <MotionPanel
        session={runtime.session}
        realm={prefix}
        enabled={runtime.commandsEnabled}
        commandsEnabled={runtime.commandsEnabled}
        clientId={runtime.clientId}
        holdsControl={runtime.holdsControl}
        jointsRef={runtime.jointsRef}
        activeTcp={runtime.status?.active_tcp ?? null}
      />
    </div>
  ),
  operate: ({ runtime, prefix }) => (
    <OperatePage
      session={runtime.session}
      realm={prefix}
      clientId={runtime.clientId}
      holdsControl={runtime.holdsControl}
      ownerUser={runtime.controlOwner?.owner?.user ?? null}
      onAcquire={runtime.acquire}
      status={runtime.status}
      jointsRef={runtime.jointsRef}
      driverAlive={runtime.driverAlive}
      commandsEnabled={runtime.commandsEnabled}
    />
  ),
  programs: ({ runtime, prefix, structure, program, onEditProgram }) => (
    <ProgramsPage
      session={runtime.session}
      realm={prefix}
      devices={structure.devices}
      program={program}
      wsConnected={runtime.wsConnected}
      jointsRef={runtime.jointsRef}
      onEdit={onEditProgram}
    />
  ),
  io: ({ runtime, prefix, structure }) => (
    <IoPage
      session={runtime.session}
      realm={prefix}
      devices={structure.devices}
      wsConnected={runtime.wsConnected}
      commandsEnabled={runtime.commandsEnabled}
      clientId={runtime.clientId}
      holdsControl={runtime.holdsControl}
    />
  ),
  cameras: ({ runtime, prefix }) => (
    <CamerasPage
      session={runtime.session}
      realm={prefix}
      wsConnected={runtime.wsConnected}
      commandsEnabled={runtime.commandsEnabled}
      producer={runtime.cameraProducer}
    />
  ),
  configuration: ({ runtime, prefix, structure, preview, onPreview, onConfigurationMutated }) => (
    <div className="flex h-full min-h-0 flex-col">
      {runtime.realm.kind === "cell" && (
        <div className="shrink-0 border-b border-zinc-950/5 p-3 dark:border-white/10">
          <h2 className="mb-2 text-sm/6 font-semibold text-zinc-950 dark:text-white">Device sources</h2>
          <DeviceTree
            session={runtime.session}
            realm={prefix}
            commandsEnabled={runtime.commandsEnabled}
            devices={structure.devices}
          />
        </div>
      )}
      <div className="min-h-0 flex-1">
        <FramesPage
          key={`${structure.frames.length}:${structure.tcps.length}:${structure.poses.length}:${structure.objects.length}`}
          session={runtime.session}
          jointsRef={runtime.jointsRef}
          flangeRef={runtime.flangeRef}
          panelOnly
          structure={structure}
          onPreviewChange={onPreview}
          onConfigurationMutated={onConfigurationMutated}
        />
      </div>
      {preview !== null && (
        <div className="shrink-0 border-t border-zinc-950/5 px-3 py-2 text-xs/5 text-zinc-500 dark:border-white/10 dark:text-zinc-400">
          Previewing <span className="font-medium text-zinc-950 dark:text-white">{preview.name}</span> in the workspace
        </div>
      )}
    </div>
  ),
};

export function RightToolPane({ tool, ctx }: { tool: WorkspaceTool; ctx: ToolPaneContext | null }) {
  if (ctx === null) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-sm/6 text-zinc-500 dark:text-zinc-400">
        Select a recording from the main navigation.
      </div>
    );
  }
  return <>{PANES[tool](ctx)}</>;
}
