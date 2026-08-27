import { ArrowUpDown, ChevronDown, ChevronUp } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { TableHeader } from "../catalyst/table";
import type { SortState } from "./useTableControls";

export function SortableHeader({
  column,
  label,
  sort,
  onToggleSort,
  filter,
  onSetFilter,
  title,
}: {
  column: string;
  label: string;
  sort: SortState | null;
  onToggleSort: (column: string) => void;
  filter?: string;
  onSetFilter?: (column: string, value: string) => void;
  title?: string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  const isActive = sort?.column === column;

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const commitFilter = () => {
    setEditing(false);
    onSetFilter?.(column, draft);
  };
  const SortIcon = isActive
    ? sort.order === "asc"
      ? ChevronUp
      : ChevronDown
    : ArrowUpDown;

  return (
    <TableHeader>
      <div className="flex items-center gap-1" title={title}>
        <div className="relative min-w-0 flex-1">
          <button
            type="button"
            className={`flex items-center gap-1 whitespace-nowrap hover:text-zinc-900 dark:hover:text-white ${editing ? "invisible" : ""}`}
            onClick={() => {
              setDraft(filter ?? "");
              setEditing(true);
            }}
          >
            {filter !== undefined && filter !== "" && (
              <span className="inline-block size-1.5 rounded-full bg-blue-500" />
            )}
            {label}
          </button>
          {editing && (
            <input
              ref={inputRef}
              aria-label={`Filter ${label}`}
              className="absolute inset-0 w-full rounded border border-zinc-300 bg-white px-1.5 py-0.5 text-xs dark:border-zinc-600 dark:bg-zinc-800"
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onBlur={commitFilter}
              onKeyDown={(event) => {
                if (event.key === "Enter") commitFilter();
                if (event.key === "Escape") setEditing(false);
              }}
            />
          )}
        </div>
        <button
          type="button"
          className="ml-auto shrink-0 p-0.5 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200"
          onClick={() => onToggleSort(column)}
          aria-label={`Sort by ${label}`}
        >
          <SortIcon className="size-3.5" />
        </button>
      </div>
    </TableHeader>
  );
}
