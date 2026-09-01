"use client";

import { Loader2, RefreshCw, Info } from "lucide-react";
import { useEffect, useState } from "react";

import { ExecutivePanelShell } from "@/components/executive/executive-panel-shell";
import { useExecutiveQuery } from "@/components/executive/use-executive-query";
import { EmptyState, ErrorState, LoadingState } from "@/components/state-blocks";
import { getMockTravelData } from "@/lib/executive/travel-mock";
import { 
  calculateTravelStats, 
  groupTripsByMonth, 
  enrichTripWithMetadata,
  type TripWithMetadata 
} from "@/lib/executive/travel-workspace-utils";
import type { ExecutiveTravelUpcomingCurated } from "@/lib/executive/types";
import { TravelSummaryCards } from "./travel-summary-cards";
import { TravelFilters } from "./travel-filters";
import { TravelTripCard } from "./travel-trip-card";
import { TravelDetailDrawer } from "./travel-detail-drawer";

export function ExecutiveTravelPanel() {
  const { data, error, loading, refresh } = useExecutiveQuery<ExecutiveTravelUpcomingCurated>(
    "/travel/upcoming",
  );
  const [refreshing, setRefreshing] = useState(false);
  const [currentFilter, setCurrentFilter] = useState<string>("all");
  const [selectedTrip, setSelectedTrip] = useState<TripWithMetadata | null>(null);

  useEffect(() => {
    if (!loading) setRefreshing(false);
  }, [loading]);

  const handleRefresh = () => {
    setRefreshing(true);
    refresh();
  };

  // Use mock data if no real trips exist (for demo purposes)
  const hasRealData = data && data.trips.length > 0;
  const displayData = hasRealData ? data : (data ? { ...data, trips: getMockTravelData().trips } : null);
  const usingMockData = !hasRealData && displayData && displayData.trips.length > 0;
  
  const allTrips = displayData?.trips ?? [];
  const showInitialLoading = loading && !data;

  // Calculate statistics
  const stats = allTrips.length > 0 ? calculateTravelStats(allTrips) : {
    upcomingTrips: 0,
    countries: [],
    flights: 0,
    hotels: 0,
    nextDeparture: null,
  };

  // Group by month
  const tripsByMonth = groupTripsByMonth(allTrips);

  // Apply filters
  const enrichedTrips = allTrips.map(enrichTripWithMetadata);
  const filteredTrips = currentFilter === "all" 
    ? enrichedTrips
    : currentFilter === "upcoming"
    ? enrichedTrips.filter((t) => t.status === "upcoming")
    : currentFilter === "completed"
    ? enrichedTrips.filter((t) => t.status === "completed")
    : enrichedTrips.filter((t) => t.country === currentFilter);

  // Re-group filtered trips
  const filteredTripsByMonth = new Map<string, TripWithMetadata[]>();
  filteredTrips.forEach((trip) => {
    const month = trip.month;
    if (!filteredTripsByMonth.has(month)) {
      filteredTripsByMonth.set(month, []);
    }
    filteredTripsByMonth.get(month)!.push(trip);
  });

  return (
    <ExecutivePanelShell>
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">Executive</p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight text-[var(--ink)]">Travel Workspace</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Comprehensive view of your executive travel schedule
          </p>
        </div>
        <button
          className="inline-flex items-center gap-2 rounded-xl border border-[var(--line)] bg-[var(--surface)] px-3 py-2 text-sm font-medium text-[var(--ink)] transition hover:bg-[var(--bg)] disabled:cursor-not-allowed disabled:opacity-60"
          disabled={loading}
          onClick={handleRefresh}
          type="button"
        >
          {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          Refresh
        </button>
      </div>

      {/* Compact demo mode notification */}
      {usingMockData ? (
        <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800">
          <Info className="h-4 w-4 flex-shrink-0" />
          <span><strong>Demo Mode:</strong> Showing sample data</span>
        </div>
      ) : null}

      {showInitialLoading ? <LoadingState label="Loading travel workspace" /> : null}
      {error ? <ErrorState message={error} /> : null}

      {!showInitialLoading && !error && allTrips.length === 0 ? (
        <EmptyState label="No travel scheduled. Your upcoming trips will appear here." />
      ) : null}

      {!error && allTrips.length > 0 ? (
        <div className="space-y-6">
          {/* Summary Cards */}
          <TravelSummaryCards stats={stats} />

          {/* Filters */}
          <TravelFilters
            currentFilter={currentFilter}
            countries={stats.countries}
            onFilterChange={setCurrentFilter}
          />

          {/* Trip Timeline */}
          {filteredTrips.length === 0 ? (
            <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-8 text-center">
              <p className="text-[var(--muted)]">No trips match the selected filter</p>
            </div>
          ) : (
            <div className="space-y-8">
              {Array.from(filteredTripsByMonth.entries()).map(([month, trips]) => (
                <section key={month}>
                  {/* Month header */}
                  <div className="mb-4 flex items-center gap-3">
                    <div className="h-px flex-1 bg-[var(--line)]" />
                    <h3 className="text-sm font-bold uppercase tracking-wide text-[var(--primary)]">
                      {month}
                    </h3>
                    <div className="h-px flex-1 bg-[var(--line)]" />
                  </div>

                  {/* Trip cards with timeline appearance */}
                  <div className="space-y-4">
                    {trips.map((trip) => (
                      <TravelTripCard
                        key={trip.id}
                        trip={trip}
                        onClick={() => setSelectedTrip(trip)}
                      />
                    ))}
                  </div>
                </section>
              ))}
            </div>
          )}
        </div>
      ) : null}

      {/* Detail Drawer */}
      <TravelDetailDrawer trip={selectedTrip} onClose={() => setSelectedTrip(null)} />
    </ExecutivePanelShell>
  );
}
