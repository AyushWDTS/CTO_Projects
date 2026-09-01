"use client";

import { Clock, Briefcase, Plane, Activity, Cloud, Globe, FileText, CheckSquare, Target } from "lucide-react";
import { formatTimeOnly } from "@/lib/executive/format";
import type { TodayStats } from "@/lib/executive/today-utils";
import type { ExecutiveTravelUpcomingCurated, ExecutiveSyncStatus } from "@/lib/executive/types";

type TodayExecutiveSidebarProps = {
  stats: TodayStats;
  travelData: ExecutiveTravelUpcomingCurated | null;
  syncData: ExecutiveSyncStatus | null;
};

export function TodayExecutiveSidebar({ stats, travelData, syncData }: TodayExecutiveSidebarProps) {
  const todayTrip = travelData?.trips.find((trip) => {
    if (!trip.starts_at) return false;
    const tripStart = new Date(trip.starts_at);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tripStart >= today && tripStart < tomorrow;
  });

  return (
    <div className="space-y-4">
      {/* Next Meeting */}
      {stats.nextMeeting ? (
        <SidebarCard icon={<Clock className="h-5 w-5 text-blue-600" />} title="Next Meeting">
          <div>
            <p className="font-semibold text-[var(--ink)] truncate">{stats.nextMeeting.title}</p>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {formatTimeOnly(stats.nextMeeting.time)}
            </p>
            {stats.nextMeeting.location ? (
              <p className="mt-1 text-xs text-[var(--muted)] truncate">
                {stats.nextMeeting.location}
              </p>
            ) : null}
          </div>
        </SidebarCard>
      ) : (
        <SidebarCard icon={<Clock className="h-5 w-5 text-gray-600" />} title="Next Meeting">
          <p className="text-sm text-[var(--muted)]">No more meetings today</p>
        </SidebarCard>
      )}

      {/* Preparation Needed */}
      {stats.pendingPreparation > 0 ? (
        <SidebarCard icon={<Briefcase className="h-5 w-5 text-amber-600" />} title="Preparation Needed">
          <p className="text-sm text-[var(--ink)]">
            {stats.pendingPreparation} meeting{stats.pendingPreparation === 1 ? "" : "s"} require preparation
          </p>
          <ul className="mt-2 space-y-1 text-xs text-[var(--muted)]">
            <li>• Review meeting materials</li>
            <li>• Prepare discussion points</li>
            <li>• Check attendee list</li>
          </ul>
        </SidebarCard>
      ) : null}

      {/* Travel Status */}
      {todayTrip ? (
        <SidebarCard icon={<Plane className="h-5 w-5 text-purple-600" />} title="Travel Today">
          <div>
            <p className="font-semibold text-[var(--ink)]">{todayTrip.headline}</p>
            <p className="mt-1 text-sm text-[var(--muted)]">{todayTrip.summary}</p>
          </div>
        </SidebarCard>
      ) : stats.travelToday ? (
        <SidebarCard icon={<Plane className="h-5 w-5 text-purple-600" />} title="Travel Today">
          <p className="text-sm text-[var(--ink)]">Travel scheduled for today</p>
        </SidebarCard>
      ) : null}

      {/* Sync Status */}
      {syncData ? (
        <SidebarCard icon={<Activity className="h-5 w-5 text-indigo-600" />} title="Sync Status">
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

      {/* AI Placeholders */}
      <SidebarCard icon={<FileText className="h-5 w-5 text-green-600" />} title="Meeting Brief">
        <p className="text-sm text-[var(--muted)]">AI-generated meeting briefs coming soon</p>
      </SidebarCard>

      <SidebarCard icon={<CheckSquare className="h-5 w-5 text-blue-600" />} title="Action Items">
        <p className="text-sm text-[var(--muted)]">Today&apos;s action items will appear here</p>
      </SidebarCard>

      <SidebarCard icon={<Target className="h-5 w-5 text-red-600" />} title="Key Decisions">
        <p className="text-sm text-[var(--muted)]">Decisions requiring attention will be tracked here</p>
      </SidebarCard>

      {/* Weather Placeholder */}
      <SidebarCard icon={<Cloud className="h-5 w-5 text-gray-600" />} title="Weather">
        <p className="text-sm text-[var(--muted)]">Weather forecast coming soon</p>
      </SidebarCard>

      {/* Timezone Placeholder */}
      <SidebarCard icon={<Globe className="h-5 w-5 text-teal-600" />} title="Timezone">
        <p className="text-sm text-[var(--muted)]">Multi-timezone support coming soon</p>
      </SidebarCard>
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
      <div className="mb-3 flex items-center gap-2">
        {icon}
        <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink)]">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function formatShortDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
}
