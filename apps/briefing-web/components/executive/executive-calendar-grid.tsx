"use client";

import { isToday, isSameMonth, type CalendarEvent } from "@/lib/executive/calendar-utils";
import { categorizeEventsForDay, getMultiDayEventPosition, getEventSpanDates } from "@/lib/executive/calendar-executive-utils";

type ExecutiveCalendarGridProps = {
  days: Date[];
  currentMonth: Date;
  events: CalendarEvent[];
  selectedDate: Date | null;
  onDateClick: (date: Date) => void;
};

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

export function ExecutiveCalendarGrid({ days, currentMonth, events, selectedDate, onDateClick }: ExecutiveCalendarGridProps) {
  // Organize days into weeks for multi-day event rendering
  const weeks: Date[][] = [];
  for (let i = 0; i < days.length; i += 7) {
    weeks.push(days.slice(i, i + 7));
  }

  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] overflow-hidden">
      {/* Weekday headers */}
      <div className="grid grid-cols-7 border-b border-[var(--line)] bg-[var(--bg)]">
        {WEEKDAYS.map((day) => (
          <div
            className="px-3 py-3 text-center text-xs font-semibold uppercase tracking-wide text-[var(--muted)]"
            key={day}
          >
            <span className="hidden lg:inline">{day}</span>
            <span className="lg:hidden">{day.substring(0, 3)}</span>
          </div>
        ))}
      </div>

      {/* Calendar grid by weeks */}
      {weeks.map((week, weekIndex) => (
        <div className="grid grid-cols-7" key={weekIndex}>
          {week.map((day, dayIndex) => {
            const { singleDay: dayEvents, multiDay: multiDayEvents } = categorizeEventsForDay(events, day);
            const isCurrentMonth = isSameMonth(day, currentMonth);
            const isTodayDate = isToday(day);
            const isSelected = selectedDate && isSameMonth(day, selectedDate) && day.getDate() === selectedDate.getDate();

            return (
              <button
                className={`relative min-h-[110px] border-b border-r border-[var(--line)] p-2 text-left transition hover:bg-[var(--bg)] ${
                  !isCurrentMonth ? "bg-[var(--surface-2)] opacity-40" : ""
                } ${isSelected ? "ring-2 ring-inset ring-[var(--primary)]" : ""} ${
                  isTodayDate ? "bg-blue-50/50" : ""
                }`}
                key={`${day.toISOString()}-${dayIndex}`}
                onClick={() => onDateClick(day)}
                type="button"
              >
                {/* Date number */}
                <div className="flex items-center justify-between mb-1">
                  <span
                    className={`inline-flex h-7 w-7 items-center justify-center rounded-full text-sm font-semibold ${
                      isTodayDate
                        ? "bg-[var(--primary)] text-white ring-2 ring-[var(--primary)] ring-offset-2"
                        : isCurrentMonth
                        ? "text-[var(--ink)]"
                        : "text-[var(--muted)]"
                    }`}
                  >
                    {day.getDate()}
                  </span>
                </div>

                {/* Multi-day events (travel) */}
                {multiDayEvents.map((event) => {
                  const position = getMultiDayEventPosition(event, day, week);
                  if (!position) return null;

                  return (
                    <div
                      className={`mb-1 truncate rounded-sm px-1.5 py-1 text-xs font-medium text-white ${
                        position.isStart ? "rounded-l-md" : ""
                      } ${position.isEnd ? "rounded-r-md" : ""}`}
                      key={event.id}
                      style={{ 
                        backgroundColor: getEventColor(event.type),
                        marginRight: position.isEnd ? "0" : "-8px",
                      }}
                      title={event.title}
                    >
                      {position.isStart ? event.title : ""}
                    </div>
                  );
                })}

                {/* Single-day events */}
                <div className="space-y-1">
                  {dayEvents.slice(0, 2).map((event) => (
                    <div
                      className="truncate rounded px-1.5 py-0.5 text-xs font-medium text-white"
                      key={event.id}
                      style={{ backgroundColor: getEventColor(event.type) }}
                      title={`${event.start.toLocaleTimeString("en-US", {
                        hour: "numeric",
                        minute: "2-digit",
                        hour12: true,
                      })} ${event.title}`}
                    >
                      {event.start.toLocaleTimeString("en-US", {
                        hour: "numeric",
                        minute: "2-digit",
                        hour12: true,
                      })}{" "}
                      {event.title}
                    </div>
                  ))}
                  {dayEvents.length > 2 ? (
                    <div className="text-xs font-medium text-[var(--muted)]">
                      +{dayEvents.length - 2} more
                    </div>
                  ) : null}
                </div>
              </button>
            );
          })}
        </div>
      ))}
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
