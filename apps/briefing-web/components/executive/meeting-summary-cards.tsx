"use client";

import { Calendar, Clock, Users, Video, Building, Globe } from "lucide-react";
import type { ExecutiveMeeting } from "@/lib/executive/types";
import { countMeetingsToday, getNextMeeting } from "@/lib/executive/meetings-utils";
import { formatExecutiveWhen } from "@/lib/executive/format";

type MeetingSummaryCardsProps = {
  allMeetings: ExecutiveMeeting[];
  weekMeetings: ExecutiveMeeting[];
};

export function MeetingSummaryCards({ allMeetings, weekMeetings }: MeetingSummaryCardsProps) {
  const totalThisWeek = weekMeetings.length;
  const todayCount = countMeetingsToday(allMeetings);
  const nextMeeting = getNextMeeting(allMeetings);
  
  // Calculate additional metrics
  const onlineMeetings = weekMeetings.filter(m => m.join_url).length;
  const externalMeetings = weekMeetings.filter(m => {
    const org = (m.organizer ?? "").toLowerCase();
    return org && !org.includes("@wdtablesystems.com") && !org.includes("@walkerdigital.com");
  }).length;
  
  // Calculate total meeting hours this week
  const totalMinutes = weekMeetings.reduce((sum, meeting) => {
    if (!meeting.start || !meeting.end) return sum;
    const start = new Date(meeting.start);
    const end = new Date(meeting.end);
    return sum + Math.round((end.getTime() - start.getTime()) / (1000 * 60));
  }, 0);
  const totalHours = Math.round(totalMinutes / 60 * 10) / 10; // Round to 1 decimal

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <SummaryCard
        icon={<Calendar className="h-5 w-5" />}
        label="This Week"
        value={String(totalThisWeek)}
        color="blue"
      />
      <SummaryCard
        icon={<Clock className="h-5 w-5" />}
        label="Meeting Hours"
        value={`${totalHours}h`}
        color="purple"
      />
      <SummaryCard
        icon={<Video className="h-5 w-5" />}
        label="Online"
        value={String(onlineMeetings)}
        color="green"
      />
      <SummaryCard
        icon={<Globe className="h-5 w-5" />}
        label="External"
        value={String(externalMeetings)}
        color="amber"
      />
      <SummaryCard
        icon={<Building className="h-5 w-5" />}
        label="Today"
        value={String(todayCount)}
        color="indigo"
      />
    </div>
  );
}

type SummaryCardProps = {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: "blue" | "purple" | "green" | "amber" | "indigo";
};

function SummaryCard({ icon, label, value, color }: SummaryCardProps) {
  const colorClasses = {
    blue: "text-blue-600",
    purple: "text-purple-600",
    green: "text-green-600",
    amber: "text-amber-600",
    indigo: "text-indigo-600",
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
