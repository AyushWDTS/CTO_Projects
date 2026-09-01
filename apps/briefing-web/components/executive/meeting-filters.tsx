"use client";

import { Filter, Calendar, Users, Video } from "lucide-react";
import type { MeetingFilter } from "@/lib/executive/meetings-utils";

type MeetingFiltersProps = {
  activeFilter: MeetingFilter;
  onFilterChange: (filter: MeetingFilter) => void;
};

const timeFilters: Array<{ id: MeetingFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "today", label: "Today" },
  { id: "this-week", label: "This Week" },
];

const typeFilters: Array<{ id: MeetingFilter; label: string }> = [
  { id: "internal", label: "Internal" },
  { id: "external", label: "External" },
  { id: "online", label: "Online" },
];

export function MeetingFilters({ activeFilter, onFilterChange }: MeetingFiltersProps) {
  return (
    <div className="space-y-3">
      {/* Time filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <Calendar className="h-4 w-4" />
          <span className="font-medium">Time:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {timeFilters.map((filter) => (
            <button
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                activeFilter === filter.id
                  ? "bg-[var(--primary)] text-white shadow-sm"
                  : "border border-[var(--line)] bg-[var(--surface)] text-[var(--ink)] hover:bg-[var(--bg)]"
              }`}
              key={filter.id}
              onClick={() => onFilterChange(filter.id)}
              type="button"
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {/* Type filters */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
          <Filter className="h-4 w-4" />
          <span className="font-medium">Type:</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {typeFilters.map((filter) => (
            <button
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                activeFilter === filter.id
                  ? "bg-[var(--primary)] text-white shadow-sm"
                  : "border border-[var(--line)] bg-[var(--surface)] text-[var(--ink)] hover:bg-[var(--bg)]"
              }`}
              key={filter.id}
              onClick={() => onFilterChange(filter.id)}
              type="button"
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
