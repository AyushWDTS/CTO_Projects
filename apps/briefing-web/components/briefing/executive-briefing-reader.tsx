"use client";

import { CircleSlash } from "lucide-react";
import { useMemo } from "react";
import { emptySectionMessage } from "@/lib/briefing-empty-messages";
import { buildBriefing, type BriefingItem, type BriefingSection } from "@/lib/briefing";
import type { Digest } from "@/lib/types";
import { SECTION_ICONS } from "@/lib/briefing-styles";
import { BookmarkButton } from "./bookmark-button";
import { UrgencyBadge } from "./badges";
import { KpiStrip } from "./kpi-strip";
import { SectionNav } from "./section-nav";
import { StoryCard } from "./story-card";

export function ExecutiveBriefingReader({
  digest,
  draftV1,
}: {
  digest: Digest;
  draftV1: boolean;
}) {
  const briefing = useMemo(() => buildBriefing(digest), [digest]);

  return (
    <div className="min-h-full bg-[var(--bg)] text-[var(--ink)]">
      <Hero
        dateLabel={briefing.dateLabel}
        draftV1={draftV1}
        generatedLabel={briefing.generatedLabel}
        windowLabel={briefing.windowLabel}
      />

      <div className="w-full px-6 lg:px-10">
        {briefing.totalItems > 0 ? <KpiStrip kpis={briefing.kpis} /> : null}

        {briefing.sections.length ? (
          <div className="sticky top-[var(--header-h)] z-20 -mx-6 mt-6 border-b border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_88%,transparent)] px-6 py-3 backdrop-blur lg:-mx-10 lg:px-10">
            <SectionNav sections={briefing.sections} />
          </div>
        ) : null}

        <main className="space-y-12 py-10">
          {briefing.totalItems === 0 ? (
            <EmptyBriefing />
          ) : (
            briefing.sections.map((section) => (
              <SectionBlock digest={digest} key={section.id} section={section} />
            ))
          )}
        </main>

        <Footer digestId={digest.id} />
      </div>
    </div>
  );
}

function Hero({
  dateLabel,
  windowLabel,
  generatedLabel,
  draftV1,
}: {
  dateLabel: string;
  windowLabel: string;
  generatedLabel: string;
  draftV1: boolean;
}) {
  return (
    <header className="border-b border-[var(--line)] bg-[var(--surface)] px-6 py-8 lg:px-10">
      <div className="w-full">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold tracking-tight text-[var(--ink)] sm:text-4xl">
            WDTS Daily News Briefing
          </h1>
          {draftV1 ? (
            <span className="inline-flex items-center rounded-full bg-[var(--warn-bg)] px-3 py-1 text-xs font-bold text-[var(--warn)] ring-1 ring-[var(--warn-line)]">
              Draft V1
            </span>
          ) : null}
        </div>
        <p className="mt-2 text-lg font-medium text-[var(--text)]">{dateLabel}</p>
        {/* <p className="mt-3 text-xs text-[var(--muted)]">
          Coverage window: {windowLabel} &nbsp;•&nbsp; Generated {generatedLabel}
        </p> */}
      </div>
    </header>
  );
}

function SectionBlock({
  section,
  digest,
}: {
  section: BriefingSection;
  digest: Digest;
}) {
  const Icon = SECTION_ICONS[section.title];
  return (
    <section data-briefing-section id={section.id}>
      <div
        className={`flex items-center gap-3 border-b pb-3 ${
          section.featured ? "border-[var(--primary-line)]" : "border-[var(--line)]"
        }`}
      >
        {Icon ? (
          <span
            className={`inline-flex h-9 w-9 items-center justify-center rounded-xl ${
              section.featured
                ? "bg-[var(--primary)] text-white"
                : "bg-[var(--surface-2)] text-[var(--muted)]"
            }`}
          >
            <Icon className="h-5 w-5" />
          </span>
        ) : null}
        <div>
          <h2
            className={`font-bold tracking-tight text-[var(--ink)] ${
              section.featured ? "text-xl sm:text-2xl" : "text-lg"
            }`}
          >
            {section.title}
          </h2>
          {section.featured ? (
            <p className="text-xs text-[var(--muted)]">
              Start here — the highest-priority intelligence today.
            </p>
          ) : null}
        </div>
      </div>

      <div className="mt-5">
        {section.isActionList ? (
          <ActionList digest={digest} items={section.items} />
        ) : section.count === 0 ? (
          <EmptySection message={emptySectionMessage(section.title)} />
        ) : section.regions ? (
          <div className="space-y-6">
            {section.regions.map((group) => (
              <div key={group.region}>
                <p className="mb-3 text-xs font-bold uppercase tracking-wider text-[var(--muted)]">
                  {group.region}
                </p>
                <div className="grid gap-4">
                  {group.items.map((item) => (
                    <StoryCard digest={digest} featured={false} item={item} key={item.raw.id} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className={section.featured ? "grid gap-5" : "grid gap-4"}>
            {section.items.map((item) => (
              <StoryCard
                digest={digest}
                featured={section.featured}
                item={item}
                key={item.raw.id}
              />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}

function ActionList({ items, digest }: { items: BriefingItem[]; digest: Digest }) {
  return (
    <div className="grid gap-2.5">
      {items.map((item) => (
        <div
          className="flex items-start gap-3 rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3"
          key={item.raw.id}
        >
          <span className="mt-0.5 text-sm font-bold text-[var(--primary)]">
            #{item.rank}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-[var(--ink)]">
              {item.headline}
            </p>
            <div className="mt-1.5 flex flex-wrap items-center gap-2">
              <UrgencyBadge urgency={item.meta.urgency} />
              <span className="text-xs text-[var(--muted)]">
                Owner: {item.meta.owner}
              </span>
            </div>
          </div>
          <BookmarkButton digest={digest} item={item} />
        </div>
      ))}
    </div>
  );
}

function EmptySection({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 rounded-2xl border border-dashed border-[var(--line)] bg-[var(--surface)] px-5 py-6">
      <CircleSlash className="h-5 w-5 shrink-0 text-[var(--muted)]" />
      <p className="text-sm text-[var(--muted)]">{message}</p>
    </div>
  );
}

function EmptyBriefing() {
  return (
    <div className="rounded-2xl border border-dashed border-[var(--line)] bg-[var(--surface)] px-6 py-16 text-center">
      <CircleSlash className="mx-auto h-8 w-8 text-[var(--muted)]" />
      <p className="mt-3 text-sm text-[var(--muted)]">
        No digest items were selected for this briefing window.
      </p>
    </div>
  );
}

function Footer({ digestId }: { digestId: string }) {
  return (
    <footer className="border-t border-[var(--line)] py-8">
      <p className="text-xs leading-relaxed text-[var(--muted)]">
        This WDTS news briefing is compiled from monitored public sources for internal review.
        Verify source material before operational or compliance decisions.
      </p>
      <p className="mt-2 text-xs text-[var(--muted)]">Digest ID: {digestId}</p>
    </footer>
  );
}
