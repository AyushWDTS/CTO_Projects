import { Filter } from "lucide-react";

type TravelFiltersProps = {
  currentFilter: string;
  countries: string[];
  onFilterChange: (filter: string) => void;
};

export function TravelFilters({ currentFilter, countries, onFilterChange }: TravelFiltersProps) {
  const statusFilters = [
    { id: "all", label: "All Trips" },
    { id: "upcoming", label: "Upcoming" },
    { id: "completed", label: "Completed" },
  ];

  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="flex items-center gap-2 text-sm text-[var(--muted)]">
        <Filter className="h-4 w-4" />
        <span className="font-medium">Filter:</span>
      </div>
      
      <div className="flex flex-wrap gap-2">
        {statusFilters.map((filter) => (
          <button
            key={filter.id}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              currentFilter === filter.id
                ? "bg-[var(--primary)] text-white"
                : "border border-[var(--line)] bg-[var(--surface)] text-[var(--ink)] hover:bg-[var(--bg)]"
            }`}
            onClick={() => onFilterChange(filter.id)}
            type="button"
          >
            {filter.label}
          </button>
        ))}
      </div>

      {countries.length > 1 ? (
        <>
          <div className="h-6 w-px bg-[var(--line)]" />
          <div className="flex flex-wrap gap-2">
            {countries.slice(0, 5).map((country) => (
              <button
                key={country}
                className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-1.5 text-sm font-medium text-[var(--ink)] transition hover:bg-[var(--bg)]"
                onClick={() => onFilterChange(country)}
                type="button"
              >
                {country}
              </button>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
