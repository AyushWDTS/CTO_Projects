import { Plane, MapPin, Hotel, Calendar } from "lucide-react";
import type { TravelStats } from "@/lib/executive/travel-workspace-utils";

type TravelSummaryCardsProps = {
  stats: TravelStats;
};

export function TravelSummaryCards({ stats }: TravelSummaryCardsProps) {
  const nextDepartureText = stats.nextDeparture
    ? `${formatShortDate(stats.nextDeparture.date)} · ${stats.nextDeparture.destination}`
    : "No upcoming trips";

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <SummaryCard
        icon={<Calendar className="h-5 w-5" />}
        label="Upcoming Trips"
        value={String(stats.upcomingTrips)}
      />
      <SummaryCard
        icon={<MapPin className="h-5 w-5" />}
        label="Countries"
        value={String(stats.countries.length)}
      />
      <SummaryCard
        icon={<Plane className="h-5 w-5" />}
        label="Flights"
        value={String(stats.flights)}
      />
      <SummaryCard
        icon={<Hotel className="h-5 w-5" />}
        label="Hotels"
        value={String(stats.hotels)}
      />
      <div className="col-span-full sm:col-span-2 lg:col-span-1">
        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
          <div className="flex items-center gap-2 text-[var(--primary)]">
            <Plane className="h-5 w-5" />
            <p className="text-xs font-semibold uppercase tracking-wide">Next Departure</p>
          </div>
          <p className="mt-2 text-sm font-medium text-[var(--ink)]">{nextDepartureText}</p>
        </div>
      </div>
    </div>
  );
}

type SummaryCardProps = {
  icon: React.ReactNode;
  label: string;
  value: string;
};

function SummaryCard({ icon, label, value }: SummaryCardProps) {
  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4">
      <div className="flex items-center gap-2 text-[var(--primary)]">
        {icon}
        <p className="text-xs font-semibold uppercase tracking-wide">{label}</p>
      </div>
      <p className="mt-2 text-2xl font-bold text-[var(--ink)]">{value}</p>
    </div>
  );
}

function formatShortDate(dateString: string | null): string {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
