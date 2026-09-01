import type { KpiMetric } from "@/lib/briefing";
import { KPI_META } from "@/lib/briefing-styles";

export function KpiStrip({ kpis }: { kpis: KpiMetric[] }) {
  return (
    <section aria-label="Briefing overview" className="mt-6">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
        Your 15-second overview
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {kpis.map((kpi) => {
          const meta = KPI_META[kpi.key];
          const Icon = meta?.icon;
          return (
            <div
              className={`relative overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-br ${
                meta?.gradient ?? ""
              } p-4 dark:border-white/10`}
              key={kpi.key}
            >
              {Icon ? (
                <span
                  className={`inline-flex h-9 w-9 items-center justify-center rounded-xl ${meta.iconWrap}`}
                >
                  <Icon className="h-5 w-5" />
                </span>
              ) : null}
              <p className="mt-3 text-3xl font-bold leading-none text-slate-900 dark:text-white">
                {kpi.value}
              </p>
              <p className="mt-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">
                {kpi.label}
              </p>
            </div>
          );
        })}
      </div>
    </section>
  );
}
