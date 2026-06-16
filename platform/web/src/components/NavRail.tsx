// Icon-only nav rail (spec §2). Only Overview and IO are live this phase;
// the other items render disabled with a "— later phase" tooltip.
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";
import { NAV_ITEMS, type PageId } from "../lib/nav";

interface NavRailProps {
  page: PageId;
  onPage: (p: PageId) => void;
}

export default function NavRail({ page, onPage }: NavRailProps) {
  return (
    <TooltipProvider>
      <nav className="flex flex-col items-center gap-1 border-r border-border bg-card py-2">
        {NAV_ITEMS.map((item) => (
          <Tooltip key={item.id}>
            <TooltipTrigger asChild>
              {/* span wrapper: tooltips still fire over disabled buttons */}
              <span>
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={!item.enabled}
                  aria-label={item.label}
                  onClick={() => onPage(item.id)}
                  className={cn(
                    "rounded-none text-base",
                    page === item.id && "border-l-2 border-[var(--tint)]",
                  )}
                >
                  {item.glyph}
                </Button>
              </span>
            </TooltipTrigger>
            <TooltipContent side="right">
              {item.enabled ? item.label : `${item.label} — later phase`}
            </TooltipContent>
          </Tooltip>
        ))}
      </nav>
    </TooltipProvider>
  );
}
