import type { ExecutiveCalendarRangeResponse, ExecutiveCalendarEvent, ExecutiveTravelTrip } from "@/lib/executive/types";

export type CalendarEvent = {
  id: string;
  title: string;
  start: Date;
  end: Date;
  type: "meeting" | "travel" | "flight" | "reminder" | "board" | "vendor" | "internal";
  location?: string;
  color?: string;
};

/**
 * Transform API calendar response to CalendarEvent format
 */
export function transformCalendarResponse(response: ExecutiveCalendarRangeResponse): CalendarEvent[] {
  const events: CalendarEvent[] = [];

  // Transform meeting events
  if (response.events) {
    response.events.forEach((event, index) => {
      const title = event.subject || "Untitled Event";
      const type = inferEventType(title, event);
      
      events.push({
        id: event.id || `event-${index}`,
        title,
        start: new Date(event.starts_at),
        end: new Date(event.ends_at),
        type,
        location: event.location || undefined,
      });
    });
  }

  // Transform travel/trip events
  if (response.trips) {
    response.trips.forEach((trip, index) => {
      const title = trip.title || "Travel";
      const type = title.toLowerCase().includes("flight") ? "flight" : "travel";
      
      // Skip trips without valid dates
      if (!trip.starts_at || !trip.ends_at) return;
      
      events.push({
        id: trip.id || `trip-${index}`,
        title,
        start: new Date(trip.starts_at),
        end: new Date(trip.ends_at),
        type,
        location: undefined,
      });
    });
  }

  return events;
}

/**
 * Infer event type from title and metadata
 */
function inferEventType(
  title: string,
  event: ExecutiveCalendarEvent
): CalendarEvent["type"] {
  const lowerTitle = title.toLowerCase();
  
  if (lowerTitle.includes("flight") || lowerTitle.includes("departure")) return "flight";
  if (lowerTitle.includes("travel") || lowerTitle.includes("trip")) return "travel";
  if (lowerTitle.includes("board") || lowerTitle.includes("executive")) return "board";
  if (lowerTitle.includes("vendor") || lowerTitle.includes("supplier")) return "vendor";
  if (lowerTitle.includes("reminder") || lowerTitle.includes("review")) return "reminder";
  if (lowerTitle.includes("internal") || lowerTitle.includes("team") || lowerTitle.includes("all-hands")) return "internal";
  
  return "meeting";
}

export function getMonthDays(year: number, month: number): Date[] {
  const firstDay = new Date(year, month, 1);
  const lastDay = new Date(year, month + 1, 0);
  const days: Date[] = [];

  // Add days from previous month to fill the first week
  const firstDayOfWeek = firstDay.getDay();
  for (let i = firstDayOfWeek - 1; i >= 0; i--) {
    const day = new Date(year, month, -i);
    days.push(day);
  }

  // Add all days of current month
  for (let day = 1; day <= lastDay.getDate(); day++) {
    days.push(new Date(year, month, day));
  }

  // Add days from next month to fill the last week
  const remainingDays = 42 - days.length; // 6 weeks * 7 days
  for (let day = 1; day <= remainingDays; day++) {
    days.push(new Date(year, month + 1, day));
  }

  return days;
}

export function isSameDay(date1: Date, date2: Date): boolean {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  );
}

export function isToday(date: Date): boolean {
  return isSameDay(date, new Date());
}

export function isSameMonth(date: Date, referenceMonth: Date): boolean {
  return (
    date.getFullYear() === referenceMonth.getFullYear() &&
    date.getMonth() === referenceMonth.getMonth()
  );
}

export function formatMonthYear(date: Date): string {
  return date.toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

export function getEventsForDay(events: CalendarEvent[], date: Date): CalendarEvent[] {
  return events.filter((event) => isSameDay(event.start, date));
}

export function getEventTypeColor(type: CalendarEvent["type"]): string {
  switch (type) {
    case "meeting":
      return "bg-blue-500";
    case "travel":
      return "bg-purple-500";
    case "flight":
      return "bg-indigo-600";
    case "reminder":
      return "bg-amber-500";
    case "board":
      return "bg-red-600";
    case "vendor":
      return "bg-green-600";
    case "internal":
      return "bg-teal-600";
    default:
      return "bg-gray-500";
  }
}

export function getEventTypeLabel(type: CalendarEvent["type"]): string {
  switch (type) {
    case "meeting":
      return "Meeting";
    case "travel":
      return "Travel";
    case "flight":
      return "Flight";
    case "reminder":
      return "Reminder";
    case "board":
      return "Board Review";
    case "vendor":
      return "Vendor Call";
    case "internal":
      return "Internal Sync";
    default:
      return "Event";
  }
}

// Mock executive calendar events
export function getMockCalendarEvents(): CalendarEvent[] {
  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();

  return [
    {
      id: "1",
      title: "Leadership Sync",
      start: new Date(year, month, 2, 9, 0),
      end: new Date(year, month, 2, 10, 0),
      type: "internal",
    },
    {
      id: "2",
      title: "Product Review",
      start: new Date(year, month, 5, 14, 0),
      end: new Date(year, month, 5, 15, 30),
      type: "meeting",
      location: "Conference Room A",
    },
    {
      id: "3",
      title: "Customer Meeting",
      start: new Date(year, month, 7, 10, 0),
      end: new Date(year, month, 7, 11, 30),
      type: "meeting",
      location: "Teams",
    },
    {
      id: "4",
      title: "Flight to Macau",
      start: new Date(year, month, 10, 15, 0),
      end: new Date(year, month, 10, 20, 0),
      type: "flight",
    },
    {
      id: "5",
      title: "Board Update Preparation",
      start: new Date(year, month, 12, 13, 0),
      end: new Date(year, month, 12, 15, 0),
      type: "board",
    },
    {
      id: "6",
      title: "Vendor Call - AI Platform",
      start: new Date(year, month, 15, 11, 0),
      end: new Date(year, month, 15, 12, 0),
      type: "vendor",
    },
    {
      id: "7",
      title: "AI Dashboard Review",
      start: new Date(year, month, 18, 16, 0),
      end: new Date(year, month, 18, 17, 0),
      type: "meeting",
    },
    {
      id: "8",
      title: "Q3 Strategy Session",
      start: new Date(year, month, 21, 9, 0),
      end: new Date(year, month, 21, 12, 0),
      type: "board",
      location: "Executive Boardroom",
    },
    {
      id: "9",
      title: "Travel: Return from Macau",
      start: new Date(year, month, 23, 8, 0),
      end: new Date(year, month, 23, 14, 0),
      type: "travel",
    },
    {
      id: "10",
      title: "Team All-Hands",
      start: new Date(year, month, 25, 15, 0),
      end: new Date(year, month, 25, 16, 0),
      type: "internal",
      location: "Town Hall",
    },
    {
      id: "11",
      title: "Review Q4 Budget",
      start: new Date(year, month, 28, 10, 0),
      end: new Date(year, month, 28, 11, 30),
      type: "meeting",
    },
    {
      id: "12",
      title: "Patent Review Reminder",
      start: new Date(year, month, 30, 9, 0),
      end: new Date(year, month, 30, 9, 30),
      type: "reminder",
    },
  ];
}
