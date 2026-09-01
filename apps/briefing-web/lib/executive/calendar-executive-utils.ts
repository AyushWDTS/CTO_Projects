import type { CalendarEvent } from "@/lib/executive/calendar-utils";
import { isSameDay, isSameMonth } from "@/lib/executive/calendar-utils";

export type CalendarStats = {
  meetingsThisMonth: number;
  travelDays: number;
  freeDays: number;
  conflicts: number;
};

/**
 * Calculate executive calendar statistics
 */
export function calculateCalendarStats(
  events: CalendarEvent[],
  currentMonth: Date
): CalendarStats {
  // Get all days in the current month
  const year = currentMonth.getFullYear();
  const month = currentMonth.getMonth();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  
  const allDaysInMonth: Date[] = [];
  for (let day = 1; day <= daysInMonth; day++) {
    allDaysInMonth.push(new Date(year, month, day));
  }
  
  // Filter events for this month
  const monthEvents = events.filter((event) => 
    isSameMonth(event.start, currentMonth)
  );
  
  // Count meetings (excluding travel)
  const meetingsThisMonth = monthEvents.filter((e) => 
    e.type === "meeting" || e.type === "internal" || e.type === "vendor" || e.type === "board" || e.type === "reminder"
  ).length;
  
  // Count days with travel
  const travelDaysSet = new Set<string>();
  monthEvents.filter((e) => e.type === "travel" || e.type === "flight").forEach((event) => {
    const start = event.start;
    const end = event.end;
    
    // Add all days between start and end
    const currentDate = new Date(start);
    while (currentDate <= end) {
      if (isSameMonth(currentDate, currentMonth)) {
        travelDaysSet.add(currentDate.toDateString());
      }
      currentDate.setDate(currentDate.getDate() + 1);
    }
  });
  const travelDays = travelDaysSet.size;
  
  // Count free days (days with no events)
  const freeDays = allDaysInMonth.filter((day) => {
    const dayEvents = events.filter((e) => isSameDay(e.start, day));
    return dayEvents.length === 0;
  }).length;
  
  // Count conflicts (days with 3+ meetings overlapping)
  const conflicts = allDaysInMonth.filter((day) => {
    const dayEvents = events.filter((e) => isSameDay(e.start, day));
    return dayEvents.length >= 5; // 5+ events in a day is considered a conflict
  }).length;
  
  return {
    meetingsThisMonth,
    travelDays,
    freeDays,
    conflicts,
  };
}

/**
 * Check if an event spans multiple days
 */
export function isMultiDayEvent(event: CalendarEvent): boolean {
  const startDate = new Date(event.start);
  startDate.setHours(0, 0, 0, 0);
  
  const endDate = new Date(event.end);
  endDate.setHours(0, 0, 0, 0);
  
  return endDate > startDate;
}

/**
 * Get all dates that an event spans
 */
export function getEventSpanDates(event: CalendarEvent): Date[] {
  const dates: Date[] = [];
  const start = new Date(event.start);
  start.setHours(0, 0, 0, 0);
  
  const end = new Date(event.end);
  end.setHours(0, 0, 0, 0);
  
  const currentDate = new Date(start);
  while (currentDate <= end) {
    dates.push(new Date(currentDate));
    currentDate.setDate(currentDate.getDate() + 1);
  }
  
  return dates;
}

/**
 * Get position info for multi-day event rendering
 */
export function getMultiDayEventPosition(
  event: CalendarEvent,
  day: Date,
  daysInWeek: Date[]
): { isStart: boolean; isEnd: boolean; spanDays: number } | null {
  const spanDates = getEventSpanDates(event);
  const isInSpan = spanDates.some((d) => isSameDay(d, day));
  
  if (!isInSpan) return null;
  
  const isStart = isSameDay(spanDates[0], day);
  const isEnd = isSameDay(spanDates[spanDates.length - 1], day);
  
  // Calculate how many days this event spans in the current week
  const weekDaysInSpan = daysInWeek.filter((d) =>
    spanDates.some((sd) => isSameDay(sd, d))
  );
  
  return {
    isStart,
    isEnd,
    spanDays: weekDaysInSpan.length,
  };
}

/**
 * Group events for a day, separating multi-day from single-day
 */
export function categorizeEventsForDay(events: CalendarEvent[], day: Date): {
  singleDay: CalendarEvent[];
  multiDay: CalendarEvent[];
} {
  const dayEvents = events.filter((event) => {
    const spanDates = getEventSpanDates(event);
    return spanDates.some((d) => isSameDay(d, day));
  });
  
  return {
    singleDay: dayEvents.filter((e) => !isMultiDayEvent(e)),
    multiDay: dayEvents.filter((e) => isMultiDayEvent(e)),
  };
}
