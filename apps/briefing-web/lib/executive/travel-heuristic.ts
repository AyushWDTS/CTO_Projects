import type { ExecutiveTravelSegment, ExecutiveTravelTrip } from "@/lib/executive/types";

const JUNK_TITLE =
  /\b(certification|jira weekly|job at|reminder|weekly update|drawings and boms|decoration|production)\b/i;
const JUNK_LOCATION =
  /\b(drawings|boms|production|decoration|weekly|jira|certification|reminder|job at)\b/i;

const TRAVEL_SEGMENT_TYPES = new Set([
  "flight",
  "hotel",
  "train",
  "car_rental",
  "car",
  "ground",
  "lodging",
  "transport",
]);

function normalizeSegmentType(value?: string | null): string {
  return (value ?? "").trim().toLowerCase().replace(/:$/, "");
}

export function isPlausibleTravelSegment(segment: ExecutiveTravelSegment): boolean {
  const type = normalizeSegmentType(segment.segment_type);
  if (!type) return false;
  if (!TRAVEL_SEGMENT_TYPES.has(type) && !type.startsWith("flight")) return false;

  const origin = (segment.origin ?? "").trim();
  const destination = (segment.destination ?? "").trim();
  if (origin && JUNK_LOCATION.test(origin)) return false;
  if (destination && JUNK_LOCATION.test(destination)) return false;
  if (origin.length > 72 || destination.length > 72) return false;

  return Boolean(origin || destination || segment.confirmation_code);
}

export function isPlausibleTravelTrip(trip: ExecutiveTravelTrip): boolean {
  if (trip.needs_review) return false;
  if (typeof trip.confidence === "number" && trip.confidence < 0.85) return false;
  if (trip.title && JUNK_TITLE.test(trip.title)) return false;

  const segments = (trip.segments ?? []).filter(isPlausibleTravelSegment);
  return segments.length > 0;
}

export function plausibleSegments(trip: ExecutiveTravelTrip): ExecutiveTravelSegment[] {
  return (trip.segments ?? []).filter(isPlausibleTravelSegment);
}

export function formatSegmentLabel(segment: ExecutiveTravelSegment): string {
  const type = normalizeSegmentType(segment.segment_type);
  if (type.startsWith("flight")) return "Flight";
  if (type === "hotel" || type === "lodging") return "Hotel";
  if (type === "train") return "Train";
  if (type === "car_rental" || type === "car") return "Car";
  if (type === "ground" || type === "transport") return "Transport";
  return type ? type.charAt(0).toUpperCase() + type.slice(1) : "Segment";
}

export function formatSegmentDetail(segment: ExecutiveTravelSegment): string {
  const parts: string[] = [];
  const origin = (segment.origin ?? "").trim();
  const destination = (segment.destination ?? "").trim();
  if (origin && destination) parts.push(`${origin} → ${destination}`);
  else if (origin || destination) parts.push(origin || destination);

  if (segment.confirmation_code) parts.push(segment.confirmation_code);
  if (segment.starts_at) parts.push(new Date(segment.starts_at).toLocaleString());
  return parts.join(" · ") || "Details pending";
}

export function heuristicTripHeadline(trip: ExecutiveTravelTrip): string {
  const title = (trip.title ?? "").trim();
  if (title && !JUNK_TITLE.test(title)) return title;

  const segments = plausibleSegments(trip);
  const first = segments[0];
  if (!first) return "Upcoming trip";

  const origin = (first.origin ?? "").trim();
  const destination = (first.destination ?? "").trim();
  if (origin && destination) return `${origin} → ${destination}`;
  return origin || destination || "Upcoming trip";
}

export function heuristicTripSummary(trip: ExecutiveTravelTrip): string {
  const segments = plausibleSegments(trip);
  const types = new Set(segments.map((segment) => formatSegmentLabel(segment)));
  const routeParts = segments
    .map((segment) => {
      const origin = (segment.origin ?? "").trim();
      const destination = (segment.destination ?? "").trim();
      if (origin && destination) return `${origin} to ${destination}`;
      return origin || destination;
    })
    .filter(Boolean);

  const uniqueRoutes = [...new Set(routeParts)].slice(0, 2);
  if (uniqueRoutes.length > 0) {
    return `${[...types].join(", ")} · ${uniqueRoutes.join("; ")}`;
  }
  return `${segments.length} confirmed segment${segments.length === 1 ? "" : "s"}`;
}

export function fallbackCuratedFromHeuristic(trip: ExecutiveTravelTrip) {
  const segments = plausibleSegments(trip);
  return {
    id: trip.id,
    headline: heuristicTripHeadline(trip),
    summary: heuristicTripSummary(trip),
    starts_at: trip.starts_at ?? segments[0]?.starts_at ?? null,
    ends_at: trip.ends_at ?? segments[segments.length - 1]?.ends_at ?? null,
    itinerary: segments.slice(0, 6).map((segment) => ({
      label: formatSegmentLabel(segment),
      detail: formatSegmentDetail(segment),
    })),
  };
}
