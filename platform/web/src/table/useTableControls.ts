import { useCallback, useState } from "react";

export interface SortState {
  column: string;
  order: "asc" | "desc";
}

export interface TableControls {
  sort: SortState | null;
  toggleSort: (column: string) => void;
  filters: Record<string, string>;
  setFilter: (column: string, value: string) => void;
  clearAll: () => void;
  hasActiveFilters: boolean;
}

export function useTableControls(): TableControls {
  const [sort, setSort] = useState<SortState | null>(null);
  const [filters, setFilters] = useState<Record<string, string>>({});

  const toggleSort = useCallback((column: string) => {
    setSort((current) => {
      if (current?.column !== column) return { column, order: "asc" };
      if (current.order === "asc") return { column, order: "desc" };
      return null;
    });
  }, []);

  const setFilter = useCallback((column: string, value: string) => {
    setFilters((current) => {
      const next = { ...current };
      const normalized = value.trim();
      if (normalized === "") delete next[column];
      else next[column] = normalized;
      return next;
    });
  }, []);

  const clearAll = useCallback(() => {
    setSort(null);
    setFilters({});
  }, []);

  return {
    sort,
    toggleSort,
    filters,
    setFilter,
    clearAll,
    hasActiveFilters: sort !== null || Object.keys(filters).length > 0,
  };
}

export type CellValue = number | string | null;

function compare(a: CellValue, b: CellValue): number {
  if (a === null) return b === null ? 0 : 1;
  if (b === null) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  return String(a).localeCompare(String(b), undefined, {
    numeric: true,
    sensitivity: "base",
  });
}

export function applyControls<T>(
  rows: T[],
  controls: TableControls,
  valueOf: (row: T, column: string) => CellValue,
): T[] {
  const filtered = rows.filter((row) =>
    Object.entries(controls.filters).every(([column, filter]) =>
      String(valueOf(row, column) ?? "")
        .toLocaleLowerCase()
        .includes(filter.toLocaleLowerCase()),
    ),
  );
  if (controls.sort === null) return filtered;
  const { column, order } = controls.sort;
  return [...filtered].sort((a, b) => {
    const result = compare(valueOf(a, column), valueOf(b, column));
    return order === "asc" ? result : -result;
  });
}
