"use client";

import { X, Calendar, MapPin, Clock, Video, Briefcase, AlertCircle, CheckCircle2 } from "lucide-react";
import { type CalendarEvent, getEventTypeLabel, isToday } from "@/lib/executive/calendar-utils";

type ExecutiveDayDetailPanelProps = {
  date: Date | null;
  events: CalendarEvent[];
  onClose: () => void;
};

export function ExecutiveDayDetailPanel({ date, events, onClose }: ExecutiveDayDetailPanelProps) {
  if (!date) {
    return null;
  }

  const dateLabel = date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  const isTodayDate = isToday(date);

  // Categorize events
  const meetings = events.filter((e) => 
    e.type === "meeting" || e.type === "internal" || e.type === "vendor" || e.type === "board"
  );
  const travel = events.filter((e) => e.type === "travel" || e.type === "flight");
  const reminders = events.filter((e) => e.type === "reminder");
  
  const isEmpty = events.length === 0;
  const hasFreeTime = meetings.length < 4; // Less than 4 meetings = has free time

  return (
    <div className="space-y-4">
      {/* Header card */}
      <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-lg font-bold text-[var(--ink)]">{dateLabel}</h3>
              {isTodayDate ? (
                <span className="rounded-full bg-[var(--primary)] px-2.5 py-0.5 text-xs font-semibold text-white">
                  Today
                </span>
              ) : null}
            </div>
            <p className="mt-1 text-sm text-[var(--muted)]">
              {events.length === 0 ? "No events scheduled" : `${events.length} event${events.length === 1 ? "" : "s"}`}
            </p>
          </div>
          <button
            className="rounded-lg p-2 text-[var(--muted)] transition hover:bg-[var(--bg)] hover:text-[var(--ink)]"
            onClick={onClose}
            type="button"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </div>

      {isEmpty ? (
        <div className="rounded-xl border border-dashed border-[var(--line)] bg-[var(--surface)] p-8 text-center">
          <Calendar className="mx-auto h-12 w-12 text-[var(--muted)]" />
          <p className="mt-3 text-sm font-medium text-[var(--ink)]">No events scheduled</p>
          <p className="mt-1 text-xs text-[var(--muted)]">This day is free of scheduled events.</p>
        </div>
      ) : (
        <>
          {/* Meetings */}
          {meetings.length > 0 ? (
            <DetailSection icon={<Briefcase className="h-5 w-5 text-blue-600" />} title="Meetings">
              <div className="space-y-2">
                {meetings.map((event) => (
                  <EventCard event={event} key={event.id} />
                ))}
              </div>
            </DetailSection>
          ) : null}

          {/* Travel */}
          {travel.length > 0 ? (
            <DetailSection icon={<MapPin className="h-5 w-5 text-purple-600" />} title="Travel">
              <div className="space-y-2">
                {travel.map((event) => (
                  <EventCard event={event} key={event.id} />
                ))}
              </div>
            </DetailSection>
          ) : null}

          {/* Action Items / Reminders */}
          {reminders.length > 0 ? (
            <DetailSection icon={<AlertCircle className="h-5 w-5 text-amber-600" />} title="Action Items">
              <div className="space-y-2">
                {reminders.map((event) => (
                  <EventCard event={event} key={event.id} />
                ))}
              </div>
            </DetailSection>
          ) : null}

          {/* Free Time Indicator */}
          {hasFreeTime ? (
            <DetailSection icon={<CheckCircle2 className="h-5 w-5 text-green-600" />} title="Free Time">
              <p className="text-sm text-[var(--muted)]">
                {meetings.length === 0 
                  ? "Full day available" 
                  : `Light schedule - ${meetings.length} meeting${meetings.length === 1 ? "" : "s"} only`}
              </p>
            </DetailSection>
          ) : null}

          {/* Preparation Section */}
          {meetings.some((m) => m.type === "board" || m.type === "vendor") ? (
            <DetailSection icon={<Briefcase className="h-5 w-5 text-indigo-600" />} title="Preparation Needed">
              <ul className="space-y-1 text-sm text-[var(--muted)]">
                {meetings.filter((m) => m.type === "board").length > 0 ? (
                  <li>• Review board materials</li>
                ) : null}
                {meetings.filter((m) => m.type === "vendor").length > 0 ? (
                  <li>• Prepare vendor discussion points</li>
                ) : null}
              </ul>
            </DetailSection>
          ) : null}
        </>
      )}
    </div>
  );
}

type DetailSectionProps = {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
};

function DetailSection({ icon, title, children }: DetailSectionProps) {
  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
      <div className="mb-3 flex items-center gap-2">
        {icon}
        <h4 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink)]">{title}</h4>
      </div>
      {children}
    </div>
  );
}

function EventCard({ event }: { event: CalendarEvent }) {
  const timeLabel = `${event.start.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  })} – ${event.end.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  })}`;

  const typeLabel = getEventTypeLabel(event.type);
  const duration = Math.round((event.end.getTime() - event.start.getTime()) / (1000 * 60));

  return (
    <div className="rounded-lg border border-[var(--line)] bg-[var(--bg)] p-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <h5 className="font-semibold text-[var(--ink)] truncate">{event.title}</h5>
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {timeLabel}
            </span>
            <span>·</span>
            <span>{duration} min</span>
            {event.location ? (
              <>
                <span>·</span>
                <span className="inline-flex items-center gap-1 truncate">
                  {event.location.toLowerCase().includes("teams") ||
                  event.location.toLowerCase().includes("zoom") ? (
                    <Video className="h-3 w-3" />
                  ) : (
                    <MapPin className="h-3 w-3" />
                  )}
                  <span className="truncate">{event.location}</span>
                </span>
              </>
            ) : null}
          </div>
        </div>
        <span
          className="flex-shrink-0 rounded-full px-2 py-0.5 text-xs font-medium text-white"
          style={{ backgroundColor: getEventColor(event.type) }}
        >
          {typeLabel}
        </span>
      </div>
    </div>
  );
}

function getEventColor(type: CalendarEvent["type"]): string {
  switch (type) {
    case "meeting":
      return "#3b82f6";
    case "travel":
      return "#a855f7";
    case "flight":
      return "#6366f1";
    case "reminder":
      return "#f59e0b";
    case "board":
      return "#dc2626";
    case "vendor":
      return "#16a34a";
    case "internal":
      return "#0d9488";
    default:
      return "#6b7280";
  }
}
