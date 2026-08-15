// Resizable side panes of the workspace (drag handle; double-click resets).
import type { PointerEvent as ReactPointerEvent, ReactNode } from "react";

function ResizeHandle({
  edge,
  width,
  onWidth,
  onReset,
}: {
  edge: "left" | "right";
  width: number;
  onWidth: (width: number) => void;
  onReset: () => void;
}) {
  const start = (event: ReactPointerEvent<HTMLDivElement>) => {
    event.currentTarget.setPointerCapture(event.pointerId);
    const originX = event.clientX;
    const originWidth = width;
    const target = event.currentTarget;
    const move = (next: PointerEvent) => {
      const delta = next.clientX - originX;
      onWidth(originWidth + (edge === "right" ? delta : -delta));
    };
    const end = () => {
      target.removeEventListener("pointermove", move);
      target.removeEventListener("pointerup", end);
      target.removeEventListener("pointercancel", end);
    };
    target.addEventListener("pointermove", move);
    target.addEventListener("pointerup", end);
    target.addEventListener("pointercancel", end);
  };

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize panel"
      title="Drag to resize; double-click to reset"
      onPointerDown={start}
      onDoubleClick={onReset}
      className={`absolute inset-y-0 z-20 w-2 cursor-col-resize touch-none outline-none after:absolute after:inset-y-0 after:left-1/2 after:w-px after:-translate-x-1/2 after:bg-transparent hover:after:bg-blue-500 ${
        edge === "right" ? "-right-1" : "-left-1"
      }`}
    />
  );
}

export function ResizablePane({
  side,
  width,
  onWidth,
  onReset,
  className = "",
  children,
}: {
  side: "left" | "right";
  width: number;
  onWidth: (width: number) => void;
  onReset: () => void;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={`@container relative h-full shrink-0 bg-white dark:bg-zinc-900 ${
        side === "left"
          ? "border-r border-zinc-950/5 dark:border-white/10"
          : "border-l border-zinc-950/5 dark:border-white/10"
      } ${className}`}
      style={{ width }}
    >
      <ResizeHandle
        edge={side === "left" ? "right" : "left"}
        width={width}
        onWidth={onWidth}
        onReset={onReset}
      />
      {children}
    </div>
  );
}
