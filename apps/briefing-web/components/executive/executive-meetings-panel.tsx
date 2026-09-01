"use client";

import { Loader2, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import { ExecutivePanelShell } from "@/components/executive/executive-panel-shell";
import { useExecutiveQuery } from "@/components/executive/use-executive-query";
import { EmptyState, ErrorState, LoadingState } from "@/components/state-blocks";
import type { ExecutiveMeetingsUpcoming, ExecutiveMeeting } from "@/lib/executive/types";
import {
  getWeekRange,
  isThisWeek,
  filterMeetingsForWeek,
  groupMeetingsByDay,
  applyMeetingFilter,
  type MeetingFilter,
} from "@/lib/executive/meetings-utils";
import { WeekNavigator } from "@/components/executive/week-navigator";
import { MeetingSummaryCards } from "@/components/executive/meeting-summary-cards";
import { MeetingFilters } from "@/components/executive/meeting-filters";
import { MeetingCard } from "@/components/executive/meeting-card";
import { MeetingDetailDrawer } from "@/components/executive/meeting-detail-drawer";
import { MeetingsExecutiveSidebar } from "@/components/executive/meetings-executive-sidebar";

export function ExecutiveMeetingsPanel() {
  const { data, error, loading, refresh } = useExecutiveQuery<ExecutiveMeetingsUpcoming>(
    "/meetings/upcoming",
    { limit: 100 },
  );
  const [refreshing, setRefreshing] = useState(false);
  const [currentWeekStart, setCurrentWeekStart] = useState(() => getWeekRange(new Date()).start);
  const [activeFilter, setActiveFilter] = useState<MeetingFilter>("all");
  const [selectedMeeting, setSelectedMeeting] = useState<ExecutiveMeeting | null>(null);

  useEffect(() => {
    if (!loading) setRefreshing(false);
  }, [loading]);

  const handleRefresh = () => {
    setRefreshing(true);
    refresh();
  };

  const handlePreviousWeek = () => {
    const prevWeek = new Date(currentWeekStart);
    prevWeek.setDate(prevWeek.getDate() - 7);
    setCurrentWeekStart(getWeekRange(prevWeek).start);
  };

  const handleThisWeek = () => {
    setCurrentWeekStart(getWeekRange(new Date()).start);
  };

  const handleNextWeek = () => {
    const nextWeek = new Date(currentWeekStart);
    nextWeek.setDate(nextWeek.getDate() + 7);
    setCurrentWeekStart(getWeekRange(nextWeek).start);
  };

  const allMeetings = data?.meetings ?? [];
  const weekRange = getWeekRange(currentWeekStart);
  const weekMeetings = filterMeetingsForWeek(allMeetings, weekRange);
  const filteredMeetings = applyMeetingFilter(weekMeetings, activeFilter);
  const dayGroups = groupMeetingsByDay(filteredMeetings, currentWeekStart);
  const showInitialLoading = loading && !data;
  const isCurrentWeek = isThisWeek(currentWeekStart);

  return (
    <ExecutivePanelShell>
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">Executive</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-[var(--ink)]">Meetings Workspace</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">Your executive meeting schedule and insights</p>
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

      {showInitialLoading ? <LoadingState label="Loading meetings workspace" /> : null}
      {error ? <ErrorState message={error} /> : null}

      {!showInitialLoading && !error ? (
        <div className="space-y-6">
          {/* Summary Cards */}
          <MeetingSummaryCards allMeetings={allMeetings} weekMeetings={weekMeetings} />

          {/* Two-column layout */}
          <div className="grid gap-6 lg:grid-cols-[1fr,380px]">
            {/* Main timeline column */}
            <div className="space-y-5">
              {/* Week Navigator */}
              <WeekNavigator
                isThisWeek={isCurrentWeek}
                onNextWeek={handleNextWeek}
                onPreviousWeek={handlePreviousWeek}
                onThisWeek={handleThisWeek}
                weekRange={weekRange}
              />

              {/* Filters */}
              <MeetingFilters
                activeFilter={activeFilter}
                onFilterChange={setActiveFilter}
              />

              {/* Day Groups */}
              {filteredMeetings.length === 0 ? (
                <EmptyState label="No meetings for the selected week and filter." />
              ) : (
                <div className="space-y-6">
                  {dayGroups.map((day) => (
                    <section key={day.date.toISOString()}>
                      <div className="mb-3 flex items-center gap-3">
                        <h3 className="text-lg font-semibold text-[var(--ink)]">
                          {day.dayLabel}
                        </h3>
                        <span className="text-sm text-[var(--muted)]">{day.dateLabel}</span>
                        {day.isToday ? (
                          <span className="rounded-full bg-[var(--primary)] px-2.5 py-0.5 text-xs font-semibold text-white">
                            Today
                          </span>
                        ) : null}
                      </div>
                      {day.meetings.length === 0 ? (
                        <p className="text-sm text-[var(--muted)]">No meetings</p>
                      ) : (
                        <div className="space-y-3">
                          {day.meetings.map((meeting) => (
                            <MeetingCard
                              key={meeting.id}
                              meeting={meeting}
                              onClick={() => setSelectedMeeting(meeting)}
                            />
                          ))}
                        </div>
                      )}
                    </section>
                  ))}
                </div>
              )}
            </div>

            {/* Executive sidebar */}
            <div className="lg:sticky lg:top-6 lg:self-start">
              <MeetingsExecutiveSidebar allMeetings={allMeetings} />
            </div>
          </div>
        </div>
      ) : null}

      <MeetingDetailDrawer
        meeting={selectedMeeting}
        onClose={() => setSelectedMeeting(null)}
      />
    </ExecutivePanelShell>
  );
}
