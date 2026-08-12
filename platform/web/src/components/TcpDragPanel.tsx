import { CircleAlert, CircleCheck, Move3d, Rotate3d, X } from "lucide-react";
import { Badge } from "../catalyst/badge";
import { Button } from "../catalyst/button";
import type { TcpDragMode } from "../scene/viewerControls";

export function TcpDragPanel({
  mode,
  allowed,
  pending,
  error,
  activeTcp,
  onMode,
  onClose,
}: {
  mode: Exclude<TcpDragMode, "off">;
  allowed: boolean;
  pending: boolean;
  error: string | null;
  activeTcp: string | null;
  onMode: (mode: Exclude<TcpDragMode, "off">) => void;
  onClose: () => void;
}) {
  return (
    <aside className="flex h-full min-h-0 flex-col bg-white dark:bg-zinc-900">
      <header className="border-b border-zinc-950/5 px-4 py-3 dark:border-white/10">
        <div className="flex items-center gap-2">
          <Move3d className="size-4 text-zinc-500 dark:text-zinc-400" />
          <h2 className="min-w-0 flex-1 text-sm/6 font-semibold text-zinc-950 dark:text-white">
            Drag active TCP
          </h2>
          <Badge color={allowed ? "blue" : "zinc"}>
            {pending ? "moving" : allowed ? "armed" : "locked"}
          </Badge>
          <Button plain aria-label="Close TCP drag controls" onClick={onClose}>
            <X data-slot="icon" />
          </Button>
        </div>
        <p className="mt-0.5 text-xs/5 text-zinc-500 dark:text-zinc-400">
          Interactive Cartesian positioning from the 3D workspace
        </p>
      </header>

      <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
        <section>
          <h3 className="mb-2 text-xs/5 font-medium text-zinc-500 dark:text-zinc-400">
            Handle mode
          </h3>
          <div className="grid grid-cols-2 gap-2">
            <Button
              {...(mode === "translate"
                ? { color: "blue" as const }
                : { outline: true as const })}
              disabled={!allowed || pending}
              onClick={() => onMode("translate")}
            >
              <Move3d data-slot="icon" />
              Translate
            </Button>
            <Button
              {...(mode === "rotate"
                ? { color: "blue" as const }
                : { outline: true as const })}
              disabled={!allowed || pending}
              onClick={() => onMode("rotate")}
            >
              <Rotate3d data-slot="icon" />
              Rotate
            </Button>
          </div>
        </section>

        <section className="rounded-lg bg-zinc-950/2.5 p-3 ring-1 ring-zinc-950/5 dark:bg-white/5 dark:ring-white/10">
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 font-mono text-xs/5">
            <dt className="text-zinc-500 dark:text-zinc-400">target</dt>
            <dd className="text-zinc-950 dark:text-white">{activeTcp ?? "flange"}</dd>
            <dt className="text-zinc-500 dark:text-zinc-400">frame</dt>
            <dd className="text-zinc-950 dark:text-white">arm/r1/base</dd>
            <dt className="text-zinc-500 dark:text-zinc-400">commit</dt>
            <dd className="text-zinc-950 dark:text-white">on handle release</dd>
          </dl>
        </section>

        <section className={`flex gap-2 rounded-lg p-3 text-xs/5 ring-1 ${
          allowed
            ? "bg-emerald-500/10 text-emerald-800 ring-emerald-500/20 dark:text-emerald-300"
            : "bg-amber-500/10 text-amber-800 ring-amber-500/20 dark:text-amber-300"
        }`}>
          {allowed ? (
            <CircleCheck className="mt-0.5 size-4 shrink-0" />
          ) : (
            <CircleAlert className="mt-0.5 size-4 shrink-0" />
          )}
          <p>
            {allowed
              ? "Drag the visible gizmo. Releasing a handle submits one move command."
              : "Live control, an alive driver, and this browser's control lease are required."}
          </p>
        </section>

        {error !== null && (
          <section className="flex gap-2 rounded-lg bg-red-500/10 p-3 text-xs/5 text-red-700 ring-1 ring-red-500/20 dark:text-red-300">
            <CircleAlert className="mt-0.5 size-4 shrink-0" />
            <p className="break-words">{error}</p>
          </section>
        )}
      </div>
    </aside>
  );
}
