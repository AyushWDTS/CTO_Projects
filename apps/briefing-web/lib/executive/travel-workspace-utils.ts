import type { ExecutiveCuratedTravelTrip } from "./types";

export type TravelStats = {
  upcomingTrips: number;
  countries: string[];
  flights: number;
  hotels: number;
  nextDeparture: {
    date: string | null;
    destination: string;
  } | null;
};

export type TripWithMetadata = ExecutiveCuratedTravelTrip & {
  destination: string;
  purpose: string;
  duration: number;
  status: "upcoming" | "in-progress" | "completed";
  month: string;
  country: string;
  hasFlights: boolean;
  hasHotel: boolean;
  hasGroundTransport: boolean;
};

/**
 * Extract destination from trip headline
 */
export function extractDestination(headline: string): string {
  // Try to extract destination from patterns like "Business Trip to Singapore"
  const toMatch = headline.match(/to\s+([^,]+)/i);
  if (toMatch) return toMatch[1].trim();
  
  // Try "Singapore Business Trip"
  const words = headline.split(" ");
  if (words.length > 0) return words[0];
  
  return headline;
}

/**
 * Extract country from destination
 */
export function extractCountry(destination: string): string {
  const countryMap: Record<string, string> = {
    singapore: "Singapore",
    macau: "Macau",
    dubai: "UAE",
    "hong kong": "Hong Kong",
    london: "UK",
    paris: "France",
    tokyo: "Japan",
    "new york": "USA",
    berlin: "Germany",
  };
  
  const lower = destination.toLowerCase();
  for (const [key, value] of Object.entries(countryMap)) {
    if (lower.includes(key)) return value;
  }
  
  return destination;
}

/**
 * Extract purpose from summary
 */
export function extractPurpose(summary: string): string {
  // Try to extract the first sentence or phrase before a period
  const firstSentence = summary.split(".")[0];
  if (firstSentence.length < 80) return firstSentence;
  
  // Fallback to first 60 characters
  return summary.substring(0, 60) + "...";
}

/**
 * Calculate trip duration in days
 */
export function calculateDuration(starts_at: string | null, ends_at: string | null): number {
  if (!starts_at || !ends_at) return 0;
  
  const start = new Date(starts_at);
  const end = new Date(ends_at);
  const diff = end.getTime() - start.getTime();
  const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
  
  return days;
}

/**
 * Determine trip status
 */
export function getTripStatus(starts_at: string | null, ends_at: string | null): "upcoming" | "in-progress" | "completed" {
  if (!starts_at || !ends_at) return "upcoming";
  
  const now = new Date();
  const start = new Date(starts_at);
  const end = new Date(ends_at);
  
  if (now < start) return "upcoming";
  if (now > end) return "completed";
  return "in-progress";
}

/**
 * Get month label from date
 */
export function getMonthLabel(dateString: string | null): string {
  if (!dateString) return "Unknown";
  
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

/**
 * Analyze itinerary for transport and accommodation
 */
export function analyzeItinerary(itinerary: Array<{ label: string; detail: string }>) {
  const hasFlights = itinerary.some((item) => 
    item.label.toLowerCase().includes("flight") || 
    item.detail.toLowerCase().includes("flight")
  );
  
  const hasHotel = itinerary.some((item) => 
    item.label.toLowerCase().includes("hotel") || 
    item.label.toLowerCase().includes("accommodation") ||
    item.label.toLowerCase().includes("stay")
  );
  
  const hasGroundTransport = itinerary.some((item) => 
    item.label.toLowerCase().includes("ground") || 
    item.label.toLowerCase().includes("transport") ||
    item.label.toLowerCase().includes("car")
  );
  
  return { hasFlights, hasHotel, hasGroundTransport };
}

/**
 * Enrich trip with metadata
 */
export function enrichTripWithMetadata(trip: ExecutiveCuratedTravelTrip): TripWithMetadata {
  const destination = extractDestination(trip.headline);
  const country = extractCountry(destination);
  const purpose = extractPurpose(trip.summary);
  const duration = calculateDuration(trip.starts_at, trip.ends_at);
  const status = getTripStatus(trip.starts_at, trip.ends_at);
  const month = getMonthLabel(trip.starts_at);
  const { hasFlights, hasHotel, hasGroundTransport } = analyzeItinerary(trip.itinerary);
  
  return {
    ...trip,
    destination,
    purpose,
    duration,
    status,
    month,
    country,
    hasFlights,
    hasHotel,
    hasGroundTransport,
  };
}

/**
 * Calculate travel statistics
 */
export function calculateTravelStats(trips: ExecutiveCuratedTravelTrip[]): TravelStats {
  const enrichedTrips = trips.map(enrichTripWithMetadata);
  const upcomingTrips = enrichedTrips.filter((t) => t.status === "upcoming").length;
  
  const countries = Array.from(new Set(enrichedTrips.map((t) => t.country)));
  
  const flights = enrichedTrips.reduce((sum, trip) => sum + (trip.hasFlights ? 1 : 0), 0);
  const hotels = enrichedTrips.reduce((sum, trip) => sum + (trip.hasHotel ? 1 : 0), 0);
  
  const nextTrip = enrichedTrips
    .filter((t) => t.status === "upcoming" && t.starts_at)
    .sort((a, b) => new Date(a.starts_at!).getTime() - new Date(b.starts_at!).getTime())[0];
  
  const nextDeparture = nextTrip ? {
    date: nextTrip.starts_at,
    destination: nextTrip.destination,
  } : null;
  
  return {
    upcomingTrips,
    countries,
    flights,
    hotels,
    nextDeparture,
  };
}

/**
 * Group trips by month
 */
export function groupTripsByMonth(trips: ExecutiveCuratedTravelTrip[]): Map<string, TripWithMetadata[]> {
  const enrichedTrips = trips.map(enrichTripWithMetadata);
  
  // Sort by start date
  enrichedTrips.sort((a, b) => {
    if (!a.starts_at) return 1;
    if (!b.starts_at) return -1;
    return new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime();
  });
  
  const grouped = new Map<string, TripWithMetadata[]>();
  
  for (const trip of enrichedTrips) {
    const month = trip.month;
    if (!grouped.has(month)) {
      grouped.set(month, []);
    }
    grouped.get(month)!.push(trip);
  }
  
  return grouped;
}

/**
 * Filter trips by criteria
 */
export function filterTrips(
  trips: TripWithMetadata[],
  filter: {
    status?: "all" | "upcoming" | "completed";
    country?: string;
    purpose?: string;
  }
): TripWithMetadata[] {
  let filtered = trips;
  
  if (filter.status && filter.status !== "all") {
    filtered = filtered.filter((t) => t.status === filter.status);
  }
  
  if (filter.country && filter.country !== "all") {
    filtered = filtered.filter((t) => t.country === filter.country);
  }
  
  if (filter.purpose) {
    const searchTerm = filter.purpose.toLowerCase();
    filtered = filtered.filter((t) => 
      t.purpose.toLowerCase().includes(searchTerm) ||
      t.summary.toLowerCase().includes(searchTerm)
    );
  }
  
  return filtered;
}
