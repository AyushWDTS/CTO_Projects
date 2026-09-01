"use client";

import { Loader2, RefreshCw, Activity } from "lucide-react";
import { useEffect, useState } from "react";
import { ExecutivePanelShell } from "./executive-panel-shell";
import { MonthNavigator } from "./month-navigator";
import { ExecutiveCalendarGrid } from "./executive-calendar-grid";
import { ExecutiveDayDetailPanel } from "./executive-day-detail-panel";
import { CalendarSummaryCards } from "./calendar-summary-cards";
import { CalendarViewSwitcher } from "./calendar-view-switcher";
import { LoadingState, EmptyState } from "../state-blocks";
import { useExecutiveQuery } from "./use-executive-query";
import { executiveCalendarRangeQuery } from "@/lib/executive-config";
import {
  getMonthDays,
  getEventsForDay,
  transformCalendarResponse,
  type CalendarEvent,
} from "@/lib/executive/calendar-utils";
import { calculateCalendarStats } from "@/lib/executive/calendar-executive-utils";
import type { ExecutiveCalendarRangeResponse, ExecutiveSyncStatus } from "@/lib/executive/types";

export function ExecutiveCalendarPanel() {
  const [currentMonth, setCurrentMonth] = useState<Date>(new Date());
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [currentView, setCurrentView] = useState<"month" | "week" | "agenda">("month");
  const [refreshing, setRefreshing] = useState(false);

  // Calculate first and last day of the displayed month
  const firstDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
  const lastDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0);

  // Fetch events for the entire month
  const rangeParams = executiveCalendarRangeQuery(firstDay, lastDay);
  const { data, error, loading, refresh } = useExecutiveQuery<ExecutiveCalendarRangeResponse>(
    "/calendar/events",
    rangeParams
  );

  // Fetch sync status
  const { data: syncData } = useExecutiveQuery<ExecutiveSyncStatus>("/sync/status");

  useEffect(() => {
    if (!loading) setRefreshing(false);
  }, [loading]);

  const handleRefresh = () => {
    setRefreshing(true);
    refresh();
  };

  // Transform API response to CalendarEvent format
  const allEvents = data ? transformCalendarResponse(data) : [];
  
  const monthDays = getMonthDays(currentMonth.getFullYear(), currentMonth.getMonth());
  const selectedDayEvents = selectedDate ? getEventsForDay(allEvents, selectedDate) : [];
  
  // Calculate executive statistics
  const stats = calculateCalendarStats(allEvents, currentMonth);

  const handlePreviousMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1, 1));
    setSelectedDate(null);
  };

  const handleNextMonth = () => {
    setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 1));
    setSelectedDate(null);
  };

  const handleToday = () => {
    const today = new Date();
    setCurrentMonth(new Date(today.getFullYear(), today.getMonth(), 1));
    setSelectedDate(today);
  };

  const handleDateClick = (date: Date) => {
    setSelectedDate(date);
  };

  const handleCloseDetail = () => {
    setSelectedDate(null);
  };

  const handleViewChange = (view: "month" | "week" | "agenda") => {
    setCurrentView(view);
    // Week and Agenda views are placeholders for now
    if (view !== "month") {
      // Could show a message or redirect in the future
    }
  };

  const syncStatus = syncData?.freshness ?? "—";
  const lastSync = syncData?.last_successful_sync 
    ? new Date(syncData.last_successful_sync).toLocaleString("en-US", { 
        month: "short", 
        day: "numeric",
        hour: "numeric",
        minute: "2-digit" 
      })
    : null;

  return (
    <ExecutivePanelShell>
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">Executive</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-[var(--ink)]">Calendar Workspace</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">Your executive schedule at a glance</p>
        </div>
        
        <div className="flex items-center gap-3">
          {/* Sync Status */}
          {syncData ? (
            <div className="flex items-center gap-2 rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm">
              <Activity className="h-4 w-4 text-[var(--primary)]" />
              <div className="flex flex-col">
                <span className="text-xs text-[var(--muted)]">Sync: {syncStatus}</span>
                {lastSync ? (
                  <span className="text-xs text-[var(--muted)]">{lastSync}</span>
                ) : null}
              </div>
            </div>
          ) : null}
          
          {/* Refresh Button */}
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
      </div>

      {loading && !data ? (
        <LoadingState label="Loading executive calendar" />
      ) : error ? (
        <EmptyState label={`Error loading calendar: ${error}`} />
      ) : (
        <div className="space-y-6">
          {/* Summary Cards */}
          <CalendarSummaryCards stats={stats} />

          {/* Navigation and View Controls */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <MonthNavigator
              currentMonth={currentMonth}
              onNextMonth={handleNextMonth}
              onPreviousMonth={handlePreviousMonth}
              onToday={handleToday}
            />
            <CalendarViewSwitcher currentView={currentView} onViewChange={handleViewChange} />
          </div>

          {/* Calendar Grid and Detail Panel */}
          {currentView === "month" ? (
            <div className="grid gap-6 lg:grid-cols-[1fr,400px]">
              <ExecutiveCalendarGrid
                currentMonth={currentMonth}
                days={monthDays}
                events={allEvents}
                onDateClick={handleDateClick}
                selectedDate={selectedDate}
              />
              {selectedDate ? (
                <div className="lg:sticky lg:top-6 lg:self-start">
                  <ExecutiveDayDetailPanel 
                    date={selectedDate} 
                    events={selectedDayEvents} 
                    onClose={handleCloseDetail} 
                  />
                </div>
              ) : (
                <div className="hidden lg:block">
                  <div className="rounded-xl border border-dashed border-[var(--line)] bg-[var(--surface)] p-8 text-center">
                    <p className="text-sm text-[var(--muted)]">Select a date to view details</p>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-8 text-center">
              <p className="text-sm font-medium text-[var(--ink)]">
                {currentView === "week" ? "Week View" : "Agenda View"}
              </p>
              <p className="mt-2 text-sm text-[var(--muted)]">
                This view is coming soon. Switch to Month view to see your calendar.
              </p>
            </div>
          )}
        </div>
      )}
    </ExecutivePanelShell>
  );
}
