"use client";

import { X, MapPin, Calendar, Clock, Plane, Hotel, Car } from "lucide-react";
import type { TripWithMetadata } from "@/lib/executive/travel-workspace-utils";

type TravelDetailDrawerProps = {
  trip: TripWithMetadata | null;
  onClose: () => void;
};

export function TravelDetailDrawer({ trip, onClose }: TravelDetailDrawerProps) {
  if (!trip) return null;

  const dateRange = formatDateRange(trip.starts_at, trip.ends_at);
  const durationText = trip.duration > 1 ? `${trip.duration} days` : `${trip.duration} day`;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden" onClick={onClose}>
      <div className="absolute inset-0 bg-black/20 backdrop-blur-sm" />
      
      <div 
        className="absolute right-0 top-0 h-full w-full max-w-2xl overflow-y-auto border-l border-[var(--line)] bg-[var(--bg)] shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 border-b border-[var(--line)] bg-[var(--surface)] px-6 py-4">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-2xl font-bold text-[var(--ink)]">{trip.destination}</h2>
              <p className="mt-1 text-sm text-[var(--muted)]">{trip.headline}</p>
            </div>
            <button
              className="rounded-lg p-2 text-[var(--muted)] transition hover:bg-[var(--bg)] hover:text-[var(--ink)]"
              onClick={onClose}
              type="button"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="space-y-6 p-6">
          {/* Summary section */}
          <section>
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--primary)]">
              Trip Summary
            </h3>
            <p className="mt-2 text-[var(--ink)]">{trip.summary}</p>
          </section>

          {/* Details grid */}
          <section className="grid gap-4 sm:grid-cols-2">
            <DetailCard icon={<Calendar className="h-5 w-5" />} label="Dates" value={dateRange} />
            <DetailCard icon={<Clock className="h-5 w-5" />} label="Duration" value={durationText} />
            <DetailCard icon={<MapPin className="h-5 w-5" />} label="Country" value={trip.country} />
            <DetailCard icon={<Plane className="h-5 w-5" />} label="Status" value={capitalize(trip.status)} />
          </section>

          {/* Itinerary */}
          {trip.itinerary.length > 0 ? (
            <section>
              <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--primary)]">
                Detailed Itinerary
              </h3>
              <ul className="mt-4 space-y-3">
                {trip.itinerary.map((item, index) => (
                  <li 
                    className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4"
                    key={`${trip.id}-itinerary-${index}`}
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-0.5 rounded-lg bg-[var(--primary)] p-2 text-white">
                        {getItineraryIcon(item.label)}
                      </div>
                      <div className="flex-1">
                        <p className="font-semibold text-[var(--ink)]">{item.label}</p>
                        <p className="mt-1 text-sm text-[var(--muted)]">{item.detail}</p>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {/* Future features placeholder */}
          <section className="rounded-xl border border-dashed border-[var(--line)] bg-[var(--surface)] p-6">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--primary)]">
              Coming Soon
            </h3>
            <div className="mt-3 grid gap-2 text-sm text-[var(--muted)]">
              <p>• Weather forecast for destination</p>
              <p>• Timezone converter</p>
              <p>• Currency exchange rates</p>
              <p>• Required travel documents</p>
              <p>• Meeting schedule during trip</p>
              <p>• Emergency contacts</p>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

type DetailCardProps = {
  icon: React.ReactNode;
  label: string;
  value: string;
};

function DetailCard({ icon, label, value }: DetailCardProps) {
  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
      <div className="flex items-center gap-2 text-[var(--primary)]">
        {icon}
        <p className="text-xs font-semibold uppercase tracking-wide">{label}</p>
      </div>
      <p className="mt-2 font-medium text-[var(--ink)]">{value}</p>
    </div>
  );
}

function getItineraryIcon(label: string): React.ReactNode {
  const lower = label.toLowerCase();
  
  if (lower.includes("flight")) {
    return <Plane className="h-4 w-4" />;
  }
  if (lower.includes("hotel") || lower.includes("accommodation") || lower.includes("stay")) {
    return <Hotel className="h-4 w-4" />;
  }
  if (lower.includes("ground") || lower.includes("transport") || lower.includes("car")) {
    return <Car className="h-4 w-4" />;
  }
  if (lower.includes("conference") || lower.includes("meeting")) {
    return <Calendar className="h-4 w-4" />;
  }
  
  return <MapPin className="h-4 w-4" />;
}

function formatDateRange(starts_at: string | null, ends_at: string | null): string {
  if (!starts_at || !ends_at) return "Date TBD";
  
  const start = new Date(starts_at);
  const end = new Date(ends_at);
  
  const startStr = start.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  const endStr = end.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
  
  return `${startStr} – ${endStr}`;
}

function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1).replace("-", " ");
}
