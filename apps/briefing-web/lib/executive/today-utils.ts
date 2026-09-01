import type { ExecutiveCalendarItem, ExecutiveTravelUpcomingCurated } from "./types";

export type TodayStats = {
  meetingsToday: number;
  nextMeeting: {
    title: string;
    time: string;
    location?: string;
  } | null;
  freeTimeRemaining: number; // in minutes
  travelToday: boolean;
  pendingPreparation: number;
};

export type TimelineBlock = {
  id: string;
  type: "meeting" | "travel" | "free" | "travel-prep";
  title: string;
  startTime: Date;
  endTime: Date;
  location?: string;
  isPast: boolean;
  isCurrent: boolean;
  isNext: boolean;
  requiresPrep?: boolean;
};

/**
 * Calculate executive statistics for today
 */
export function calculateTodayStats(
  calendarItems: ExecutiveCalendarItem[],
  travelData: ExecutiveTravelUpcomingCurated | null
): TodayStats {
  const now = new Date();
  
  // Count meetings
  const meetingsToday = calendarItems.length;
  
  // Find next meeting
  const upcomingMeetings = calendarItems
    .filter((item) => {
      const start = (item as any).starts_at || item.start;
      return start && new Date(start) > now;
    })
    .sort((a, b) => {
      const startA = (a as any).starts_at || a.start;
      const startB = (b as any).starts_at || b.start;
      return new Date(startA).getTime() - new Date(startB).getTime();
    });
  
  const nextMeetingItem = upcomingMeetings[0];
  const nextMeeting = nextMeetingItem
    ? {
        title: (nextMeetingItem as any).subject || nextMeetingItem.title || "Untitled",
        time: (nextMeetingItem as any).starts_at || nextMeetingItem.start || "",
        location: nextMeetingItem.location || undefined,
      }
    : null;
  
  // Calculate free time remaining (time until EOD minus meeting time)
  const endOfDay = new Date();
  endOfDay.setHours(17, 0, 0, 0); // 5 PM
  
  const remainingMinutes = Math.max(0, (endOfDay.getTime() - now.getTime()) / (1000 * 60));
  
  const upcomingMeetingTime = upcomingMeetings.reduce((total, item) => {
    const start = new Date((item as any).starts_at || item.start);
    const end = new Date((item as any).ends_at || item.end);
    return total + (end.getTime() - start.getTime()) / (1000 * 60);
  }, 0);
  
  const freeTimeRemaining = Math.max(0, Math.round(remainingMinutes - upcomingMeetingTime));
  
  // Check for travel today
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const tomorrow = new Date(today);
  tomorrow.setDate(tomorrow.getDate() + 1);
  
  const travelToday = travelData?.trips.some((trip) => {
    if (!trip.starts_at) return false;
    const tripStart = new Date(trip.starts_at);
    return tripStart >= today && tripStart < tomorrow;
  }) ?? false;
  
  // Count items needing preparation (external meetings, board meetings)
  const pendingPreparation = upcomingMeetings.filter((item) => {
    const title = ((item as any).subject || item.title || "").toLowerCase();
    const organizer = (item.organizer || "").toLowerCase();
    
    const isExternal = organizer && 
      !organizer.includes("@wdtablesystems.com") && 
      !organizer.includes("@walkerdigital.com");
    
    const isBoard = title.includes("board") || title.includes("executive");
    
    return isExternal || isBoard;
  }).length;
  
  return {
    meetingsToday,
    nextMeeting,
    freeTimeRemaining,
    travelToday,
    pendingPreparation,
  };
}

/**
 * Build today's timeline with meetings and free time blocks
 */
export function buildTodayTimeline(
  calendarItems: ExecutiveCalendarItem[]
): TimelineBlock[] {
  const now = new Date();
  const startOfDay = new Date();
  startOfDay.setHours(8, 0, 0, 0); // 8 AM
  const endOfDay = new Date();
  endOfDay.setHours(17, 0, 0, 0); // 5 PM
  
  const blocks: TimelineBlock[] = [];
  
  // Convert calendar items to timeline blocks (WITHOUT isNext calculation)
  const meetingBlocks: TimelineBlock[] = calendarItems.map((item, index) => {
    const start = new Date((item as any).starts_at || item.start);
    const end = new Date((item as any).ends_at || item.end);
    const title = (item as any).subject || item.title || "Untitled";
    const organizer = item.organizer || "";
    
    const isExternal = organizer && 
      !organizer.includes("@wdtablesystems.com") && 
      !organizer.includes("@walkerdigital.com");
    
    return {
      id: item.id || `meeting-${index}`,
      type: "meeting" as const,
      title,
      startTime: start,
      endTime: end,
      location: item.location || undefined,
      isPast: end < now,
      isCurrent: start <= now && end > now,
      isNext: false, // Will be calculated after sorting
      requiresPrep: isExternal || title.toLowerCase().includes("board"),
    };
  });
  
  // Sort by start time
  meetingBlocks.sort((a, b) => a.startTime.getTime() - b.startTime.getTime());
  
  // Calculate isNext AFTER all blocks are created and sorted
  const upcomingMeetings = meetingBlocks.filter((b) => b.startTime > now);
  if (upcomingMeetings.length > 0) {
    upcomingMeetings[0].isNext = true;
  }
  
  // Add free time blocks between meetings
  let currentTime = startOfDay;
  
  meetingBlocks.forEach((meeting, index) => {
    // Add free time before this meeting
    if (meeting.startTime > currentTime) {
      const freeMinutes = (meeting.startTime.getTime() - currentTime.getTime()) / (1000 * 60);
      if (freeMinutes >= 15) { // Only show free blocks of 15+ minutes
        blocks.push({
          id: `free-${index}`,
          type: "free",
          title: "Free Time",
          startTime: new Date(currentTime),
          endTime: new Date(meeting.startTime),
          isPast: meeting.startTime < now,
          isCurrent: currentTime <= now && meeting.startTime > now,
          isNext: false,
        });
      }
    }
    
    // Add the meeting
    blocks.push(meeting);
    currentTime = new Date(Math.max(currentTime.getTime(), meeting.endTime.getTime()));
  });
  
  // Add final free time block until end of day
  if (currentTime < endOfDay) {
    blocks.push({
      id: "free-eod",
      type: "free",
      title: "Free Time",
      startTime: new Date(currentTime),
      endTime: new Date(endOfDay),
      isPast: false,
      isCurrent: currentTime <= now && endOfDay > now,
      isNext: currentTime > now,
    });
  }
  
  return blocks;
}

/**
 * Format duration in a human-readable way
 */
export function formatDuration(minutes: number): string {
  if (minutes < 60) {
    return `${minutes}m`;
  }
  
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
}

/**
 * Calculate duration between two dates in minutes
 */
export function calculateDurationMinutes(start: Date, end: Date): number {
  return Math.round((end.getTime() - start.getTime()) / (1000 * 60));
}
