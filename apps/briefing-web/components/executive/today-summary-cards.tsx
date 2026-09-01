"use client";

import { Calendar, Clock, Coffee, Plane, AlertCircle } from "lucide-react";
import { formatTimeOnly } from "@/lib/executive/format";
import type { TodayStats } from "@/lib/executive/today-utils";

type TodaySummaryCardsProps = {
  stats: TodayStats;
};

export function TodaySummaryCards({ stats }: TodaySummaryCardsProps) {
  const freeTimeDisplay = stats.freeTimeRemaining >= 60
    ? `${Math.floor(stats.freeTimeRemaining / 60)}h ${stats.freeTimeRemaining % 60}m`
    : `${stats.freeTimeRemaining}m`;

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <SummaryCard
        icon={<Calendar className="h-5 w-5" />}
        label="Meetings Today"
        value={String(stats.meetingsToday)}
        color="blue"
      />
      <SummaryCard
        icon={<Clock className="h-5 w-5" />}
        label="Next Meeting"
        value={stats.nextMeeting ? formatTimeOnly(stats.nextMeeting.time) : "None"}
        subtitle={stats.nextMeeting?.title}
        color="purple"
      />
      <SummaryCard
        icon={<Coffee className="h-5 w-5" />}
        label="Free Time Left"
        value={freeTimeDisplay}
        color="green"
      />
      <SummaryCard
        icon={<Plane className="h-5 w-5" />}
        label="Travel Today"
        value={stats.travelToday ? "Yes" : "No"}
        color={stats.travelToday ? "amber" : "gray"}
      />
      <SummaryCard
        icon={<AlertCircle className="h-5 w-5" />}
        label="Needs Prep"
        value={String(stats.pendingPreparation)}
        color="red"
      />
    </div>
  );
}

type SummaryCardProps = {
  icon: React.ReactNode;
  label: string;
  value: string;
  subtitle?: string;
  color: "blue" | "purple" | "green" | "amber" | "red" | "gray";
};

function SummaryCard({ icon, label, value, subtitle, color }: SummaryCardProps) {
  const colorClasses = {
    blue: "text-blue-600",
    purple: "text-purple-600",
    green: "text-green-600",
    amber: "text-amber-600",
    red: "text-red-600",
    gray: "text-gray-600",
  };

  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
      <div className={`flex items-center gap-2 ${colorClasses[color]}`}>
        {icon}
        <p className="text-xs font-semibold uppercase tracking-wide">{label}</p>
      </div>
      <p className="mt-2 text-2xl font-bold text-[var(--ink)]">{value}</p>
      {subtitle ? (
        <p className="mt-1 text-xs text-[var(--muted)] truncate">{subtitle}</p>
      ) : null}
    </div>
  );
}
