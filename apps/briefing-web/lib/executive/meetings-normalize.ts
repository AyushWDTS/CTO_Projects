import type { ExecutiveMeeting, ExecutiveMeetingsUpcoming } from "@/lib/executive/types";

type RawMeeting = {
  id: string;
  subject?: string;
  title?: string;
  starts_at?: string;
  start?: string;
  ends_at?: string;
  end?: string;
  organizer_email?: string;
  organizer?: string;
  location?: string;
  join_url?: string;
  [key: string]: unknown;
};

type RawMeetingsUpcoming = {
  as_of: string;
  from_time: string;
  meetings: RawMeeting[];
};

export function normalizeMeetingsResponse(raw: RawMeetingsUpcoming): ExecutiveMeetingsUpcoming {
  return {
    as_of: raw.as_of,
    from_time: raw.from_time,
    meetings: raw.meetings.map(normalizeMeeting),
  };
}

export function normalizeSingleMeeting(raw: RawMeeting): ExecutiveMeeting {
  return normalizeMeeting(raw);
}

function normalizeMeeting(raw: RawMeeting): ExecutiveMeeting {
  return {
    id: raw.id,
    title: raw.title ?? raw.subject ?? undefined,
    start: raw.start ?? raw.starts_at ?? undefined,
    end: raw.end ?? raw.ends_at ?? undefined,
    organizer: raw.organizer ?? raw.organizer_email ?? undefined,
    location: raw.location ?? undefined,
    join_url: raw.join_url ?? undefined,
    provider: raw.provider as string | undefined,
    attendees: raw.attendees as any,
    body_preview: raw.body_preview as string | undefined,
  };
}
