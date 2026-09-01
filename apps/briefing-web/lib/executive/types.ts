/** DTOs derived from live WDTS Executive REST responses (gateway /executive/api). */

export type ExecutiveProviderStatus = {
  provider: string;
  connected: boolean;
  mailbox?: string | null;
  last_sync?: string | null;
  resources?: string[];
  freshness?: string;
};

export type ExecutiveSyncError = {
  id: number;
  provider: string;
  code: string | null;
  message: string;
  occurred_at: string;
};

export type ExecutiveSyncStatus = {
  as_of: string;
  freshness: string;
  providers: ExecutiveProviderStatus[];
  last_successful_sync: string | null;
  errors: ExecutiveSyncError[];
};

export type ExecutiveCalendarItem = {
  id?: string;
  title?: string;
  start?: string;
  end?: string;
  location?: string | null;
  organizer?: string | null;
  provider?: string;
  [key: string]: unknown;
};

export type ExecutiveCalendarAgenda = {
  date?: string;
  timezone: string;
  items: ExecutiveCalendarItem[];
  conflicts: unknown[];
  warnings: unknown[];
  providers: ExecutiveProviderStatus[];
  as_of: string;
  week_start?: string;
  week_end?: string;
};

/**
 * Response shape for range-based calendar endpoint.
 * Used by /calendar/events API.
 */
export type ExecutiveCalendarRangeResponse = {
  start: string;
  end: string;
  range_start: string;
  range_end: string;
  timezone: string;
  as_of: string;
  events: ExecutiveCalendarEvent[];
  trips: ExecutiveTravelTrip[];
};

export type ExecutiveCalendarEvent = {
  id: string;
  meeting_id?: string;
  subject: string;
  starts_at: string;
  ends_at: string;
  location?: string | null;
  organizer?: string | null;
  join_url?: string | null;
  is_online_meeting?: boolean;
  is_all_day?: boolean;
};

export type ExecutiveMeetingAttendee = {
  email: string;
  display_name?: string;
  role?: string;
  response_status?: string;
};

export type ExecutiveMeeting = {
  id: string;
  title?: string;
  start?: string;
  end?: string;
  organizer?: string | null;
  location?: string | null;
  join_url?: string | null;
  provider?: string;
  attendees?: ExecutiveMeetingAttendee[];
  body_preview?: string;
  [key: string]: unknown;
};

export type ExecutiveMeetingDetail = ExecutiveMeeting & {
  attendees: ExecutiveMeetingAttendee[];
};

export type ExecutiveMeetingsUpcoming = {
  as_of: string;
  from_time: string;
  meetings: ExecutiveMeeting[];
};

export type ExecutiveTravelSegment = {
  id: string;
  segment_type?: string;
  provider_name?: string | null;
  confirmation_code?: string | null;
  starts_at?: string | null;
  ends_at?: string | null;
  origin?: string | null;
  destination?: string | null;
  status?: string;
  confidence?: number;
  needs_review?: boolean;
  [key: string]: unknown;
};

export type ExecutiveTravelTrip = {
  id: string;
  title?: string;
  status?: string;
  starts_at?: string | null;
  ends_at?: string | null;
  confidence?: number;
  needs_review?: boolean;
  segments?: ExecutiveTravelSegment[];
  segments_count?: number;
  [key: string]: unknown;
};

export type ExecutiveTravelUpcoming = {
  as_of: string;
  refresh_enqueued?: boolean;
  sync_run_id?: string | null;
  trips: ExecutiveTravelTrip[];
};

export type ExecutiveCuratedTravelItineraryItem = {
  label: string;
  detail: string;
};

export type ExecutiveCuratedTravelTrip = {
  id: string;
  headline: string;
  summary: string;
  starts_at: string | null;
  ends_at: string | null;
  itinerary: ExecutiveCuratedTravelItineraryItem[];
};

export type ExecutiveTravelUpcomingCurated = {
  as_of: string;
  trips: ExecutiveCuratedTravelTrip[];
  curation?: {
    method: "bedrock" | "heuristic";
    source_count: number;
    published_count: number;
  };
};
