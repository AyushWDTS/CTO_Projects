import { categoryClass, CATEGORY_ICONS, urgencyClass } from "@/lib/briefing-styles";

const BADGE_BASE =
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold";

export function UrgencyBadge({ urgency }: { urgency: string }) {
  return <span className={`${BADGE_BASE} ${urgencyClass(urgency)}`}>{urgency}</span>;
}

export function CategoryBadge({ category }: { category: string }) {
  const Icon = CATEGORY_ICONS[category];
  return (
    <span className={`${BADGE_BASE} ${categoryClass(category)}`}>
      {Icon ? <Icon className="h-3.5 w-3.5" /> : null}
      {category}
    </span>
  );
}

export function OwnerBadge({ owner }: { owner: string }) {
  return (
    <span className={`${BADGE_BASE} bg-slate-100 text-slate-600 ring-1 ring-slate-200 dark:bg-white/5 dark:text-slate-300 dark:ring-white/10`}>
      {owner}
    </span>
  );
}

export function RankBadge({ rank, featured }: { rank: number; featured?: boolean }) {
  if (featured) {
    return (
      <span className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-slate-900 to-slate-700 text-sm font-bold text-white shadow-sm dark:from-sky-500 dark:to-blue-600">
        {rank}
      </span>
    );
  }
  return (
    <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-md bg-slate-900 px-1.5 text-xs font-bold text-white dark:bg-sky-500/90">
      #{rank}
    </span>
  );
}
