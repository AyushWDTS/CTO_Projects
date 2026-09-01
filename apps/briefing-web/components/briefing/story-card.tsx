"use client";

import {
  CalendarDays,
  ChevronDown,
  ExternalLink,
  Globe,
  Lightbulb,
  Newspaper,
  Target,
  UserRound,
} from "lucide-react";
import { useState } from "react";
import { BookmarkButton } from "@/components/briefing/bookmark-button";
import type { BriefingItem } from "@/lib/briefing";
import type { Digest } from "@/lib/types";
import { CategoryBadge, OwnerBadge, RankBadge, UrgencyBadge } from "./badges";

export function StoryCard({
  item,
  featured,
  digest,
}: {
  item: BriefingItem;
  featured: boolean;
  digest?: Digest | null;
}) {
  const cardClass = featured
    ? "group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-[0_8px_30px_rgb(15,23,42,0.06)] transition hover:shadow-[0_12px_40px_rgb(15,23,42,0.10)] dark:border-white/10 dark:bg-slate-900/70 dark:shadow-[0_8px_30px_rgb(0,0,0,0.35)]"
    : "group relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:border-slate-300 hover:shadow-md dark:border-white/10 dark:bg-slate-900/60 dark:hover:border-white/20";

  return (
    <article className={`${cardClass} animate-fade-in-up`}>
      {featured ? (
        <span className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-sky-500 via-blue-500 to-indigo-500" />
      ) : null}

      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <RankBadge featured={featured} rank={item.rank} />
          <div className="flex flex-wrap items-center gap-2">
            <UrgencyBadge urgency={item.meta.urgency} />
            <CategoryBadge category={item.meta.category} />
            {featured ? <OwnerBadge owner={item.meta.owner} /> : null}
          </div>
        </div>
        <BookmarkButton digest={digest} item={item} />
      </div>

      <h3
        className={`mt-4 font-semibold leading-snug text-slate-900 dark:text-slate-50 ${
          featured ? "text-lg sm:text-xl" : "text-base"
        }`}
      >
        {item.headline}
      </h3>

      {item.summary ? (
        <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {item.summary}
        </p>
      ) : null}

      {item.whyItMatters ? (
        <div className="mt-4 rounded-xl border-l-4 border-sky-500 bg-sky-50/70 px-4 py-3 dark:border-sky-400 dark:bg-sky-500/10">
          <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-sky-700 dark:text-sky-300">
            <Lightbulb className="h-3.5 w-3.5" />
            Why it matters to WDTS
          </p>
          <p className="mt-1 text-sm leading-relaxed text-slate-700 dark:text-slate-200">
            {item.whyItMatters}
          </p>
        </div>
      ) : null}

      {item.suggestedAction ? (
        <div className="mt-3 rounded-xl border-l-4 border-orange-500 bg-orange-50/70 px-4 py-3 dark:border-orange-400 dark:bg-orange-500/10">
          <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wide text-orange-700 dark:text-orange-300">
            <Target className="h-3.5 w-3.5" />
            Suggested action
          </p>
          <p className="mt-1 text-sm leading-relaxed text-slate-700 dark:text-slate-200">
            {item.suggestedAction}
          </p>
        </div>
      ) : null}

      <Details item={item} />
    </article>
  );
}

function Details({ item }: { item: BriefingItem }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-4 border-t border-slate-100 pt-3 dark:border-white/5">
      <button
        className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 transition hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
        onClick={() => setOpen((value) => !value)}
        type="button"
      >
        <ChevronDown className={`h-3.5 w-3.5 transition ${open ? "rotate-180" : ""}`} />
        {open ? "Hide details" : "Show details"}
      </button>
      {open ? (
        <dl className="mt-3 grid gap-2 text-xs text-slate-500 dark:text-slate-400 sm:grid-cols-2">
          <Meta icon={<Newspaper className="h-3.5 w-3.5" />} label="Source" value={item.meta.sourceName || "Unknown source"} />
          <Meta icon={<CalendarDays className="h-3.5 w-3.5" />} label="Date" value={item.meta.eventDate || "Unknown"} />
          <Meta icon={<Globe className="h-3.5 w-3.5" />} label="Region" value={item.meta.region || "Unknown"} />
          <Meta icon={<UserRound className="h-3.5 w-3.5" />} label="Owner" value={item.meta.owner} />
          {item.sourceUrl ? (
            <div className="sm:col-span-2">
              <a
                className="inline-flex items-center gap-1.5 font-semibold text-sky-600 hover:text-sky-700 dark:text-sky-400 dark:hover:text-sky-300"
                href={item.sourceUrl}
                rel="noreferrer"
                target="_blank"
              >
                <ExternalLink className="h-3.5 w-3.5" />
                Read original source
              </a>
            </div>
          ) : null}
        </dl>
      ) : null}
    </div>
  );
}

function Meta({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-slate-400 dark:text-slate-500">{icon}</span>
      <span className="font-semibold text-slate-600 dark:text-slate-300">{label}:</span>
      <span className="truncate">{value}</span>
    </div>
  );
}
