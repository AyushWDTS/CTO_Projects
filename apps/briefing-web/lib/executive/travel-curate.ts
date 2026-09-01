import type {
  ExecutiveCuratedTravelTrip,
  ExecutiveTravelUpcoming,
  ExecutiveTravelUpcomingCurated,
} from "@/lib/executive/types";
import { curateTravelWithBedrock } from "@/lib/executive/travel-bedrock";
import { fallbackCuratedFromHeuristic, isPlausibleTravelTrip } from "@/lib/executive/travel-heuristic";

export type { ExecutiveTravelUpcomingCurated };

function curationMode(): "bedrock" | "heuristic" {
  const mode = (process.env.WDTS_EXECUTIVE_TRAVEL_CURATION ?? "bedrock").trim().toLowerCase();
  if (mode === "heuristic" || mode === "off") return "heuristic";
  return "bedrock";
}

export async function curateExecutiveTravel(
  payload: ExecutiveTravelUpcoming,
): Promise<ExecutiveTravelUpcomingCurated> {
  const sourceTrips = payload.trips ?? [];
  const mode = curationMode();

  if (mode === "heuristic") {
    const trips = sourceTrips.filter(isPlausibleTravelTrip).map(fallbackCuratedFromHeuristic);
    return {
      as_of: payload.as_of,
      trips,
      curation: {
        method: "heuristic",
        source_count: sourceTrips.length,
        published_count: trips.length,
      },
    };
  }

  const { trips, method } = await curateTravelWithBedrock(sourceTrips);
  return {
    as_of: payload.as_of,
    trips,
    curation: {
      method,
      source_count: sourceTrips.length,
      published_count: trips.length,
    },
  };
}
