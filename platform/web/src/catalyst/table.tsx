import clsx from "clsx";
import type React from "react";
import { createContext, useContext } from "react";

const TableContext = createContext({
  bleed: false,
  dense: false,
  grid: false,
  striped: false,
});

export function Table({
  bleed = false,
  dense = false,
  grid = false,
  striped = false,
  className,
  children,
  ...props
}: {
  bleed?: boolean;
  dense?: boolean;
  grid?: boolean;
  striped?: boolean;
} & React.ComponentPropsWithoutRef<"div">) {
  return (
    <TableContext.Provider value={{ bleed, dense, grid, striped }}>
      <div className="flow-root">
        <div
          {...props}
          className={clsx(
            className,
            "-mx-(--gutter) overflow-x-auto whitespace-nowrap",
          )}
        >
          <div
            className={clsx(
              "inline-block min-w-full align-middle",
              !bleed && "sm:px-(--gutter)",
            )}
          >
            <table className="min-w-full text-left text-sm/6 text-zinc-950 dark:text-white">
              {children}
            </table>
          </div>
        </div>
      </div>
    </TableContext.Provider>
  );
}

export function TableHead({
  className,
  ...props
}: React.ComponentPropsWithoutRef<"thead">) {
  return (
    <thead
      {...props}
      className={clsx(className, "text-zinc-500 dark:text-zinc-400")}
    />
  );
}

export function TableBody(props: React.ComponentPropsWithoutRef<"tbody">) {
  return <tbody {...props} />;
}

export function TableRow({
  className,
  ...props
}: React.ComponentPropsWithoutRef<"tr">) {
  const { striped } = useContext(TableContext);
  return (
    <tr
      {...props}
      className={clsx(
        className,
        striped && "even:bg-zinc-950/2.5 dark:even:bg-white/2.5",
      )}
    />
  );
}

export function TableHeader({
  className,
  ...props
}: React.ComponentPropsWithoutRef<"th">) {
  const { bleed, grid } = useContext(TableContext);
  return (
    <th
      {...props}
      className={clsx(
        className,
        "border-b border-b-zinc-950/10 px-3 py-2 font-medium first:pl-(--gutter,--spacing(2)) last:pr-(--gutter,--spacing(2)) dark:border-b-white/10",
        grid &&
          "border-l border-l-zinc-950/5 first:border-l-0 dark:border-l-white/5",
        !bleed && "sm:first:pl-1 sm:last:pr-1",
      )}
    />
  );
}

export function TableCell({
  className,
  ...props
}: React.ComponentPropsWithoutRef<"td">) {
  const { bleed, dense, grid, striped } = useContext(TableContext);
  return (
    <td
      {...props}
      className={clsx(
        className,
        "relative px-3 first:pl-(--gutter,--spacing(2)) last:pr-(--gutter,--spacing(2))",
        !striped && "border-b border-zinc-950/5 dark:border-white/5",
        grid &&
          "border-l border-l-zinc-950/5 first:border-l-0 dark:border-l-white/5",
        dense ? "py-2" : "py-4",
        !bleed && "sm:first:pl-1 sm:last:pr-1",
      )}
    />
  );
}
