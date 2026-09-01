"use client";

import { X, Calendar, MapPin, Clock, Video } from "lucide-react";
import { type CalendarEvent, getEventTypeLabel } from "@/lib/executive/calendar-utils";

type DayDetailPanelProps = {
  date: Date | null;
  events: CalendarEvent[];
  onClose: () => void;
};

export function DayDetailPanel({ date, events, onClose }: DayDetailPanelProps) {
  if (!date) {
    return null;
  }

  const dateLabel = date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  const groupedEvents = {
    meetings: events.filter((e) => e.type === "meeting"),
    travel: events.filter((e) => e.type === "travel" || e.type === "flight"),
    internal: events.filter((e) => e.type === "internal" || e.type === "vendor"),
    reminders: events.filter((e) => e.type === "reminder" || e.type === "board"),
  };

  const isEmpty = events.length === 0;

  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-[var(--ink)]">{dateLabel}</h3>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {events.length === 0 ? "No events" : `${events.length} event${events.length === 1 ? "" : "s"}`}
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

      {isEmpty ? (
        <div className="mt-6 rounded-lg border border-dashed border-[var(--line)] bg-[var(--bg)] p-8 text-center">
          <Calendar className="mx-auto h-12 w-12 text-[var(--muted)]" />
          <p className="mt-3 text-sm font-medium text-[var(--muted)]">No events scheduled</p>
          <p className="mt-1 text-xs text-[var(--muted)]">This day is free of scheduled events.</p>
        </div>
      ) : (
        <div className="mt-6 space-y-6">
          {groupedEvents.meetings.length > 0 ? (
            <EventSection title="Meetings" events={groupedEvents.meetings} />
          ) : null}
          {groupedEvents.travel.length > 0 ? (
            <EventSection title="Travel & Flights" events={groupedEvents.travel} />
          ) : null}
          {groupedEvents.internal.length > 0 ? (
            <EventSection title="Internal & Vendor" events={groupedEvents.internal} />
          ) : null}
          {groupedEvents.reminders.length > 0 ? (
            <EventSection title="Reminders & Reviews" events={groupedEvents.reminders} />
          ) : null}
        </div>
      )}
    </div>
  );
}

function EventSection({ title, events }: { title: string; events: CalendarEvent[] }) {
  return (
    <div>
      <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">{title}</h4>
      <div className="space-y-3">
        {events.map((event) => (
          <EventCard event={event} key={event.id} />
        ))}
      </div>
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
    <div className="rounded-lg border border-[var(--line)] bg-[var(--bg)] p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <h5 className="font-semibold text-[var(--ink)]">{event.title}</h5>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-[var(--muted)]">
            <span className="inline-flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {timeLabel}
            </span>
            <span>·</span>
            <span>{duration} min</span>
            {event.location ? (
              <>
                <span>·</span>
                <span className="inline-flex items-center gap-1">
                  {event.location.toLowerCase().includes("teams") ||
                  event.location.toLowerCase().includes("zoom") ? (
                    <Video className="h-3 w-3" />
                  ) : (
                    <MapPin className="h-3 w-3" />
                  )}
                  {event.location}
                </span>
              </>
            ) : null}
          </div>
        </div>
        <span
          className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium text-white`}
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
