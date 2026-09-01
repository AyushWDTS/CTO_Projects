"use client";

import { Clock, AlertCircle, Plane, Activity } from "lucide-react";
import { formatExecutiveWhen, formatTimeOnly } from "@/lib/executive/format";
import type { ExecutiveMeeting, ExecutiveSyncStatus, ExecutiveTravelUpcomingCurated } from "@/lib/executive/types";
import { getNextMeeting } from "@/lib/executive/meetings-utils";
import { useExecutiveQuery } from "./use-executive-query";

type MeetingsExecutiveSidebarProps = {
  allMeetings: ExecutiveMeeting[];
};

export function MeetingsExecutiveSidebar({ allMeetings }: MeetingsExecutiveSidebarProps) {
  const nextMeeting = getNextMeeting(allMeetings);
  
  // Fetch travel and sync data
  const { data: travelData } = useExecutiveQuery<ExecutiveTravelUpcomingCurated>("/travel/upcoming");
  const { data: syncData } = useExecutiveQuery<ExecutiveSyncStatus>("/sync/status");
  
  // Meetings that need preparation (external or have many attendees)
  const needsPrep = allMeetings.filter((m) => {
    const isUpcoming = m.start && new Date(m.start) > new Date();
    const isExternal = (m.organizer ?? "").toLowerCase() &&
      !(m.organizer ?? "").toLowerCase().includes("@wdtablesystems.com") &&
      !(m.organizer ?? "").toLowerCase().includes("@walkerdigital.com");
    const hasMany = (m.attendees?.length ?? 0) > 5;
    return isUpcoming && (isExternal || hasMany);
  }).slice(0, 3);
  
  const upcomingTrips = travelData?.trips.slice(0, 2) ?? [];

  return (
    <div className="space-y-4">
      {/* Next Meeting */}
      <SidebarCard
        icon={<Clock className="h-5 w-5 text-blue-600" />}
        title="Next Meeting"
      >
        {nextMeeting ? (
          <div>
            <p className="font-semibold text-[var(--ink)]">
              {nextMeeting.title || "Untitled"}
            </p>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {formatExecutiveWhen(nextMeeting.start)}
            </p>
            {nextMeeting.location ? (
              <p className="mt-1 text-xs text-[var(--muted)]">
                {nextMeeting.location}
              </p>
            ) : null}
          </div>
        ) : (
          <p className="text-sm text-[var(--muted)]">No upcoming meetings</p>
        )}
      </SidebarCard>

      {/* Needs Preparation */}
      {needsPrep.length > 0 ? (
        <SidebarCard
          icon={<AlertCircle className="h-5 w-5 text-amber-600" />}
          title="Needs Preparation"
        >
          <ul className="space-y-2">
            {needsPrep.map((meeting) => (
              <li 
                className="rounded-lg border border-[var(--line)] bg-[var(--bg)] px-3 py-2"
                key={meeting.id}
              >
                <p className="text-sm font-medium text-[var(--ink)] truncate">
                  {meeting.title || "Untitled"}
                </p>
                <p className="mt-0.5 text-xs text-[var(--muted)]">
                  {meeting.start ? formatTimeOnly(meeting.start) : "Time TBD"}
                </p>
              </li>
            ))}
          </ul>
        </SidebarCard>
      ) : null}

      {/* Upcoming Travel */}
      {upcomingTrips.length > 0 ? (
        <SidebarCard
          icon={<Plane className="h-5 w-5 text-green-600" />}
          title="Upcoming Travel"
        >
          <ul className="space-y-2">
            {upcomingTrips.map((trip) => (
              <li 
                className="rounded-lg border border-[var(--line)] bg-[var(--bg)] px-3 py-2"
                key={trip.id}
              >
                <p className="text-sm font-medium text-[var(--ink)]">
                  {trip.headline}
                </p>
                <p className="mt-0.5 text-xs text-[var(--muted)]">
                  {trip.starts_at ? formatShortDate(trip.starts_at) : "Date TBD"}
                </p>
              </li>
            ))}
          </ul>
        </SidebarCard>
      ) : null}

      {/* Sync Status */}
      {syncData ? (
        <SidebarCard
          icon={<Activity className="h-5 w-5 text-purple-600" />}
          title="Sync Status"
        >
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-[var(--muted)]">Freshness:</span>
              <span className="font-medium text-[var(--ink)]">{syncData.freshness ?? "—"}</span>
            </div>
            {syncData.last_successful_sync ? (
              <div className="flex justify-between">
                <span className="text-[var(--muted)]">Last sync:</span>
                <span className="font-medium text-[var(--ink)]">
                  {formatShortDate(syncData.last_successful_sync)}
                </span>
              </div>
            ) : null}
          </div>
        </SidebarCard>
      ) : null}
    </div>
  );
}

type SidebarCardProps = {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
};

function SidebarCard({ icon, title, children }: SidebarCardProps) {
  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink)]">
          {title}
        </h3>
      </div>
      {children}
    </div>
  );
}

function formatShortDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
