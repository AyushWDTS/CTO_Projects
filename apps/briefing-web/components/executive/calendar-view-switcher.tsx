"use client";

type CalendarViewSwitcherProps = {
  currentView: "month" | "week" | "agenda";
  onViewChange: (view: "month" | "week" | "agenda") => void;
};

export function CalendarViewSwitcher({ currentView, onViewChange }: CalendarViewSwitcherProps) {
  const views: Array<{ id: "month" | "week" | "agenda"; label: string }> = [
    { id: "month", label: "Month" },
    { id: "week", label: "Week" },
    { id: "agenda", label: "Agenda" },
  ];

  return (
    <div className="inline-flex rounded-lg border border-[var(--line)] bg-[var(--surface)] p-1">
      {views.map((view) => (
        <button
          className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
            currentView === view.id
              ? "bg-[var(--primary)] text-white shadow-sm"
              : "text-[var(--ink)] hover:bg-[var(--bg)]"
          }`}
          key={view.id}
          onClick={() => onViewChange(view.id)}
          type="button"
        >
          {view.label}
        </button>
      ))}
    </div>
  );
}
