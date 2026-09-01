"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

type MonthNavigatorProps = {
  currentMonth: Date;
  onPreviousMonth: () => void;
  onNextMonth: () => void;
  onToday: () => void;
};

export function MonthNavigator({
  currentMonth,
  onPreviousMonth,
  onNextMonth,
  onToday,
}: MonthNavigatorProps) {
  const monthLabel = currentMonth.toLocaleDateString("en-US", {
    month: "long",
    year: "numeric",
  });

  return (
    <div className="flex items-center gap-3">
      <button
        className="inline-flex items-center gap-1 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm font-medium text-[var(--ink)] transition hover:bg-[var(--bg)]"
        onClick={onPreviousMonth}
        type="button"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>
      <button
        className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-4 py-2 text-sm font-semibold text-[var(--ink)] transition hover:bg-[var(--bg)]"
        onClick={onToday}
        type="button"
      >
        Today
      </button>
      <button
        className="inline-flex items-center gap-1 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm font-medium text-[var(--ink)] transition hover:bg-[var(--bg)]"
        onClick={onNextMonth}
        type="button"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
      <h3 className="ml-2 text-lg font-bold text-[var(--ink)]">{monthLabel}</h3>
    </div>
  );
}
