import type { ExecutiveMeeting } from "@/lib/executive/types";

export type WeekRange = {
  start: Date;
  end: Date;
  label: string;
};

export type DayGroup = {
  date: Date;
  dayLabel: string;
  dateLabel: string;
  meetings: ExecutiveMeeting[];
  isToday: boolean;
};

export type MeetingFilter = "all" | "today" | "this-week" | "internal" | "external" | "online";

export function getWeekRange(date: Date): WeekRange {
  const start = new Date(date);
  start.setHours(0, 0, 0, 0);
  const day = start.getDay();
  const diff = start.getDate() - day + (day === 0 ? -6 : 1);
  start.setDate(diff);

  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  end.setHours(23, 59, 59, 999);

  const startStr = formatShortDate(start);
  const endStr = formatShortDate(end);
  const label = `${startStr} – ${endStr}`;

  return { start, end, label };
}

export function isThisWeek(date: Date): boolean {
  const now = new Date();
  const thisWeek = getWeekRange(now);
  return date >= thisWeek.start && date <= thisWeek.end;
}

export function isSameDay(d1: Date, d2: Date): boolean {
  return (
    d1.getFullYear() === d2.getFullYear() &&
    d1.getMonth() === d2.getMonth() &&
    d1.getDate() === d2.getDate()
  );
}

export function formatShortDate(date: Date): string {
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function groupMeetingsByDay(meetings: ExecutiveMeeting[], weekStart: Date): DayGroup[] {
  const days: DayGroup[] = [];
  const today = new Date();

  for (let i = 0; i < 7; i++) {
    const date = new Date(weekStart);
    date.setDate(weekStart.getDate() + i);
    date.setHours(0, 0, 0, 0);

    const dayMeetings = meetings.filter((meeting) => {
      if (!meeting.start) return false;
      const meetingDate = new Date(meeting.start);
      return isSameDay(meetingDate, date);
    });

    days.push({
      date,
      dayLabel: date.toLocaleDateString("en-US", { weekday: "long" }),
      dateLabel: formatShortDate(date),
      meetings: dayMeetings.sort((a, b) => {
        if (!a.start) return 1;
        if (!b.start) return -1;
        return new Date(a.start).getTime() - new Date(b.start).getTime();
      }),
      isToday: isSameDay(date, today),
    });
  }

  return days;
}

export function filterMeetingsForWeek(meetings: ExecutiveMeeting[], weekRange: WeekRange): ExecutiveMeeting[] {
  return meetings.filter((meeting) => {
    if (!meeting.start) return false;
    const meetingDate = new Date(meeting.start);
    return meetingDate >= weekRange.start && meetingDate <= weekRange.end;
  });
}

export function applyMeetingFilter(meetings: ExecutiveMeeting[], filter: MeetingFilter, userEmail?: string): ExecutiveMeeting[] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  switch (filter) {
    case "today":
      return meetings.filter((m) => m.start && isSameDay(new Date(m.start), today));
    case "this-week":
      return meetings.filter((m) => m.start && isThisWeek(new Date(m.start)));
    case "internal":
      return meetings.filter((m) => {
        const org = (m.organizer ?? "").toLowerCase();
        return org.includes("@wdtablesystems.com") || org.includes("@walkerdigital.com");
      });
    case "external":
      return meetings.filter((m) => {
        const org = (m.organizer ?? "").toLowerCase();
        return org && !org.includes("@wdtablesystems.com") && !org.includes("@walkerdigital.com");
      });
    case "online":
      return meetings.filter((m) => Boolean(m.join_url));
    default:
      return meetings;
  }
}

export function getNextMeeting(meetings: ExecutiveMeeting[]): ExecutiveMeeting | null {
  const now = new Date();
  const upcoming = meetings
    .filter((m) => m.start && new Date(m.start) > now)
    .sort((a, b) => new Date(a.start!).getTime() - new Date(b.start!).getTime());
  return upcoming[0] ?? null;
}

export function countMeetingsToday(meetings: ExecutiveMeeting[]): number {
  const today = new Date();
  return meetings.filter((m) => m.start && isSameDay(new Date(m.start), today)).length;
}
