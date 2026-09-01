import { MapPin, Calendar, Clock, Plane, Hotel, Car, ChevronRight } from "lucide-react";
import type { TripWithMetadata } from "@/lib/executive/travel-workspace-utils";

type TravelTripCardProps = {
  trip: TripWithMetadata;
  onClick: () => void;
};

export function TravelTripCard({ trip, onClick }: TravelTripCardProps) {
  const dateRange = formatDateRange(trip.starts_at, trip.ends_at);
  const durationText = trip.duration > 1 ? `${trip.duration} days` : `${trip.duration} day`;

  return (
    <button
      className="group relative w-full overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5 text-left transition hover:border-[var(--primary)] hover:shadow-lg"
      onClick={onClick}
      type="button"
    >
      {/* Timeline indicator */}
      <div className="absolute left-0 top-0 h-full w-1 bg-[var(--primary)]" />
      
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-3">
          {/* Destination (hero text) */}
          <div>
            <h3 className="text-2xl font-bold text-[var(--ink)] group-hover:text-[var(--primary)]">
              {trip.destination}
            </h3>
            <p className="mt-1 text-sm text-[var(--muted)]">{trip.purpose}</p>
          </div>

          {/* Date, Duration, Status */}
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-1.5 text-[var(--ink)]">
              <Calendar className="h-4 w-4 text-[var(--muted)]" />
              <span>{dateRange}</span>
            </div>
            <div className="flex items-center gap-1.5 text-[var(--ink)]">
              <Clock className="h-4 w-4 text-[var(--muted)]" />
              <span>{durationText}</span>
            </div>
            <StatusBadge status={trip.status} />
          </div>

          {/* Travel summary icons */}
          <div className="flex items-center gap-3">
            {trip.hasFlights ? (
              <div className="flex items-center gap-1.5 rounded-lg bg-[var(--bg)] px-2 py-1 text-xs text-[var(--ink)]">
                <Plane className="h-3.5 w-3.5 text-[var(--primary)]" />
                <span>Flight</span>
              </div>
            ) : null}
            {trip.hasHotel ? (
              <div className="flex items-center gap-1.5 rounded-lg bg-[var(--bg)] px-2 py-1 text-xs text-[var(--ink)]">
                <Hotel className="h-3.5 w-3.5 text-[var(--primary)]" />
                <span>Hotel</span>
              </div>
            ) : null}
            {trip.hasGroundTransport ? (
              <div className="flex items-center gap-1.5 rounded-lg bg-[var(--bg)] px-2 py-1 text-xs text-[var(--ink)]">
                <Car className="h-3.5 w-3.5 text-[var(--primary)]" />
                <span>Ground</span>
              </div>
            ) : null}
          </div>
        </div>

        {/* Country badge and arrow */}
        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-1.5 rounded-lg border border-[var(--line)] bg-[var(--bg)] px-2 py-1 text-xs font-medium text-[var(--ink)]">
            <MapPin className="h-3.5 w-3.5 text-[var(--primary)]" />
            <span>{trip.country}</span>
          </div>
          <ChevronRight className="h-5 w-5 text-[var(--muted)] transition group-hover:translate-x-1 group-hover:text-[var(--primary)]" />
        </div>
      </div>
    </button>
  );
}

type StatusBadgeProps = {
  status: "upcoming" | "in-progress" | "completed";
};

function StatusBadge({ status }: StatusBadgeProps) {
  const config = {
    upcoming: { label: "Upcoming", color: "bg-blue-100 text-blue-700 border-blue-200" },
    "in-progress": { label: "In Progress", color: "bg-green-100 text-green-700 border-green-200" },
    completed: { label: "Completed", color: "bg-gray-100 text-gray-600 border-gray-200" },
  };

  const { label, color } = config[status];

  return (
    <span className={`rounded-full border px-2.5 py-0.5 text-xs font-semibold ${color}`}>
      {label}
    </span>
  );
}

function formatDateRange(starts_at: string | null, ends_at: string | null): string {
  if (!starts_at || !ends_at) return "Date TBD";
  
  const start = new Date(starts_at);
  const end = new Date(ends_at);
  
  const startStr = start.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  const endStr = end.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  
  return `${startStr} – ${endStr}`;
}
