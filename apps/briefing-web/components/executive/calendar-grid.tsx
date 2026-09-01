"use client";

import { isToday, isSameMonth, getEventsForDay, type CalendarEvent } from "@/lib/executive/calendar-utils";

type CalendarGridProps = {
  days: Date[];
  currentMonth: Date;
  events: CalendarEvent[];
  selectedDate: Date | null;
  onDateClick: (date: Date) => void;
};

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function CalendarGrid({ days, currentMonth, events, selectedDate, onDateClick }: CalendarGridProps) {
  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] overflow-hidden">
      {/* Weekday headers */}
      <div className="grid grid-cols-7 border-b border-[var(--line)] bg-[var(--bg)]">
        {WEEKDAYS.map((day) => (
          <div
            className="px-2 py-3 text-center text-xs font-semibold uppercase tracking-wide text-[var(--muted)]"
            key={day}
          >
            {day}
          </div>
        ))}
      </div>

      {/* Calendar grid */}
      <div className="grid grid-cols-7">
        {days.map((day, index) => {
          const dayEvents = getEventsForDay(events, day);
          const isCurrentMonth = isSameMonth(day, currentMonth);
          const isTodayDate = isToday(day);
          const isSelected = selectedDate && isSameMonth(day, selectedDate) && day.getDate() === selectedDate.getDate();

          return (
            <button
              className={`min-h-[100px] border-b border-r border-[var(--line)] p-2 text-left transition hover:bg-[var(--bg)] ${
                !isCurrentMonth ? "bg-[var(--surface-2)] opacity-50" : ""
              } ${isSelected ? "ring-2 ring-inset ring-[var(--primary)]" : ""}`}
              key={`${day.toISOString()}-${index}`}
              onClick={() => onDateClick(day)}
              type="button"
            >
              <div className="flex items-center justify-between">
                <span
                  className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-sm font-medium ${
                    isTodayDate
                      ? "bg-[var(--primary)] text-white"
                      : isCurrentMonth
                      ? "text-[var(--ink)]"
                      : "text-[var(--muted)]"
                  }`}
                >
                  {day.getDate()}
                </span>
              </div>
              {dayEvents.length > 0 ? (
                <div className="mt-1 space-y-1">
                  {dayEvents.slice(0, 3).map((event) => (
                    <div
                      className="truncate rounded px-1.5 py-0.5 text-xs font-medium text-white"
                      key={event.id}
                      style={{ backgroundColor: getEventColor(event.type) }}
                    >
                      {event.start.toLocaleTimeString("en-US", {
                        hour: "numeric",
                        minute: "2-digit",
                        hour12: true,
                      })}{" "}
                      {event.title}
                    </div>
                  ))}
                  {dayEvents.length > 3 ? (
                    <div className="text-xs text-[var(--muted)]">+{dayEvents.length - 3} more</div>
                  ) : null}
                </div>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function getEventColor(type: CalendarEvent["type"]): string {
  switch (type) {
    case "meeting":
      return "#3b82f6"; // blue
    case "travel":
      return "#a855f7"; // purple
    case "flight":
      return "#6366f1"; // indigo
    case "reminder":
      return "#f59e0b"; // amber
    case "board":
      return "#dc2626"; // red
    case "vendor":
      return "#16a34a"; // green
    case "internal":
      return "#0d9488"; // teal
    default:
      return "#6b7280"; // gray
  }
}
