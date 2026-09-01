"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { ExecutivePanelShell } from "@/components/executive/executive-panel-shell";
import { useExecutiveQuery } from "@/components/executive/use-executive-query";
import { EmptyState, ErrorState, LoadingState } from "@/components/state-blocks";
import { executiveCalendarQuery } from "@/lib/executive-config";
import type { ExecutiveCalendarAgenda, ExecutiveCalendarItem, ExecutiveSyncStatus, ExecutiveTravelUpcomingCurated } from "@/lib/executive/types";
import { TodaySummaryCards } from "./today-summary-cards";
import { TodayTimeline } from "./today-timeline";
import { TodayExecutiveSidebar } from "./today-executive-sidebar";
import { calculateTodayStats, buildTodayTimeline } from "@/lib/executive/today-utils";

/**
 * Deduplicate calendar events that appear multiple times with same subject/time.
 * The API sometimes returns the same event as both "calendar_event" and "meeting" types.
 */
function deduplicateEvents(items: ExecutiveCalendarItem[]): ExecutiveCalendarItem[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    const subject = (item as any).subject || item.title || "";
    const start = (item as any).starts_at || item.start || "";
    const key = `${subject}:${start}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function ExecutiveTodayPanel() {
  const calendarParams = executiveCalendarQuery();
  const { data: syncData, loading: syncLoading, error: syncError } = useExecutiveQuery<ExecutiveSyncStatus>("/sync/status");
  const { data: agendaData, loading: agendaLoading, error: agendaError, refresh: refreshAgenda } = useExecutiveQuery<ExecutiveCalendarAgenda>("/calendar/today", calendarParams);
  const { data: travelData, loading: travelLoading, error: travelError } = useExecutiveQuery<ExecutiveTravelUpcomingCurated>("/travel/upcoming");

  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    if (!agendaLoading) setRefreshing(false);
  }, [agendaLoading]);

  const handleRefresh = () => {
    setRefreshing(true);
    refreshAgenda();
  };

  const loading = syncLoading || agendaLoading || travelLoading;
  const error = syncError ?? agendaError ?? travelError;

  // Deduplicate and process events
  const calendarItems = agendaData ? deduplicateEvents(agendaData.items) : [];
  
  // Calculate statistics and build timeline
  const stats = calculateTodayStats(calendarItems, travelData ?? null);
  const timelineBlocks = buildTodayTimeline(calendarItems);

  return (
    <ExecutivePanelShell>
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">Executive</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-[var(--ink)]">Command Center</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Your executive dashboard for today · {agendaData?.date ? new Date(agendaData.date).toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" }) : ""}
          </p>
        </div>
        
        <button
          className="inline-flex items-center gap-2 rounded-xl border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm font-medium text-[var(--ink)] transition hover:bg-[var(--bg)] disabled:cursor-not-allowed disabled:opacity-60"
          disabled={loading}
          onClick={handleRefresh}
          type="button"
        >
          {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Refresh
        </button>
      </div>

      {loading && !agendaData ? (
        <LoadingState label="Loading command center" />
      ) : error ? (
        <ErrorState message={error} />
      ) : (
        <div className="space-y-6">
          {/* Summary Cards */}
          <TodaySummaryCards stats={stats} />

          {/* Two-column layout: Timeline + Sidebar */}
          <div className="grid gap-6 lg:grid-cols-[1fr,380px]">
            {/* Main Timeline */}
            <div>
              <TodayTimeline blocks={timelineBlocks} />
            </div>

            {/* Executive Sidebar */}
            <div className="lg:sticky lg:top-6 lg:self-start">
              <TodayExecutiveSidebar 
                stats={stats}
                travelData={travelData ?? null}
                syncData={syncData ?? null}
              />
            </div>
          </div>
        </div>
      )}
    </ExecutivePanelShell>
  );
}
