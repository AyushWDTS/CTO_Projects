"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import type { WeekRange } from "@/lib/executive/meetings-utils";

type WeekNavigatorProps = {
  weekRange: WeekRange;
  onPreviousWeek: () => void;
  onThisWeek: () => void;
  onNextWeek: () => void;
  isThisWeek: boolean;
};

export function WeekNavigator({
  weekRange,
  onPreviousWeek,
  onThisWeek,
  onNextWeek,
  isThisWeek,
}: WeekNavigatorProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        className="inline-flex items-center gap-1 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm font-medium text-[var(--ink)] transition hover:bg-[var(--bg)]"
        onClick={onPreviousWeek}
        type="button"
      >
        <ChevronLeft className="h-4 w-4" />
        Previous Week
      </button>
      <button
        className="inline-flex items-center gap-1 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm font-medium text-[var(--ink)] transition hover:bg-[var(--bg)] disabled:cursor-not-allowed disabled:opacity-50"
        disabled={isThisWeek}
        onClick={onThisWeek}
        type="button"
      >
        This Week
      </button>
      <button
        className="inline-flex items-center gap-1 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm font-medium text-[var(--ink)] transition hover:bg-[var(--bg)]"
        onClick={onNextWeek}
        type="button"
      >
        Next Week
        <ChevronRight className="h-4 w-4" />
      </button>
      <div className="flex-1 text-center">
        <p className="text-sm font-semibold text-[var(--ink)]">{weekRange.label}</p>
      </div>
    </div>
  );
}
