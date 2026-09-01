"use client";

import { Calendar, Plane, Coffee, AlertTriangle } from "lucide-react";
import type { CalendarStats } from "@/lib/executive/calendar-executive-utils";

type CalendarSummaryCardsProps = {
  stats: CalendarStats;
};

export function CalendarSummaryCards({ stats }: CalendarSummaryCardsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <SummaryCard
        icon={<Calendar className="h-5 w-5" />}
        label="Meetings"
        value={String(stats.meetingsThisMonth)}
        color="blue"
      />
      <SummaryCard
        icon={<Plane className="h-5 w-5" />}
        label="Travel Days"
        value={String(stats.travelDays)}
        color="purple"
      />
      <SummaryCard
        icon={<Coffee className="h-5 w-5" />}
        label="Free Days"
        value={String(stats.freeDays)}
        color="green"
      />
      <SummaryCard
        icon={<AlertTriangle className="h-5 w-5" />}
        label="Conflicts"
        value={String(stats.conflicts)}
        color="amber"
      />
    </div>
  );
}

type SummaryCardProps = {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: "blue" | "purple" | "green" | "amber";
};

function SummaryCard({ icon, label, value, color }: SummaryCardProps) {
  const colorClasses = {
    blue: "text-blue-600",
    purple: "text-purple-600",
    green: "text-green-600",
    amber: "text-amber-600",
  };

  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
      <div className={`flex items-center gap-2 ${colorClasses[color]}`}>
        {icon}
        <p className="text-xs font-semibold uppercase tracking-wide">{label}</p>
      </div>
      <p className="mt-2 text-2xl font-bold text-[var(--ink)]">{value}</p>
    </div>
  );
}
