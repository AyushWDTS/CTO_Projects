"use client";

import { Bookmark, CalendarDays, Newspaper } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { BookmarkProvider } from "@/components/briefing/bookmark-context";
import { BookmarksPanel } from "@/components/briefing/bookmarks-panel";
import { ExecutiveBriefingReader } from "@/components/briefing/executive-briefing-reader";
import { HistoryPanel } from "@/components/briefing/history-panel";
import { ErrorState, LoadingState } from "@/components/state-blocks";
import { fetchJson } from "@/lib/api";
import type { Digest, ListResponse } from "@/lib/types";

type DailyBriefingViewProps = {
  /** Shown under the section title for operators vs executives. */
  helperText?: string;
};

type BriefingTab = "today" | "history" | "bookmarks";

const TABS: { id: BriefingTab; label: string; icon: typeof Newspaper }[] = [
  { id: "today", label: "Today", icon: Newspaper },
  { id: "history", label: "History", icon: CalendarDays },
  { id: "bookmarks", label: "Bookmarks", icon: Bookmark },
];

export function DailyBriefingView({
  helperText = "Latest WDTS daily news briefing.",
}: DailyBriefingViewProps) {
  return (
    <BookmarkProvider>
      <DailyBriefingViewInner helperText={helperText} />
    </BookmarkProvider>
  );
}

function DailyBriefingViewInner({ helperText }: { helperText: string }) {
  const [tab, setTab] = useState<BriefingTab>("today");
  const [digest, setDigest] = useState<Digest | null>(null);
  const [loadingDigest, setLoadingDigest] = useState(true);
  const [digestError, setDigestError] = useState<string | null>(null);

  const loadLatest = useCallback(async () => {
    setLoadingDigest(true);
    setDigestError(null);
    try {
      const list = await fetchJson<ListResponse<Digest>>("/api/v1/digests", {
        limit: 1,
        offset: 0,
      });
      const latest = list.items[0];
      if (!latest) {
        setDigest(null);
        return;
      }
      const detail = await fetchJson<Digest>(`/api/v1/digests/${latest.id}`);
      setDigest(detail);
    } catch (err: unknown) {
      setDigest(null);
      setDigestError(err instanceof Error ? err.message : "Failed to load briefing.");
    } finally {
      setLoadingDigest(false);
    }
  }, []);

  useEffect(() => {
    void loadLatest();
  }, [loadLatest]);

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
            Daily Briefing
          </p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">WDTS news briefing</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">{helperText}</p>
        </div>
        {tab === "today" ? (
          <button
            className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-1.5 text-sm font-medium text-[var(--ink)] hover:bg-[var(--surface-2)]"
            onClick={() => void loadLatest()}
            type="button"
          >
            Refresh
          </button>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2 border-b border-[var(--line)] pb-3">
        {TABS.map(({ id, label, icon: Icon }) => {
          const active = tab === id;
          return (
            <button
              className={`inline-flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm font-semibold transition ${
                active
                  ? "bg-[var(--primary)] text-white"
                  : "border border-[var(--line)] bg-[var(--surface)] text-[var(--ink)] hover:bg-[var(--surface-2)]"
              }`}
              key={id}
              onClick={() => setTab(id)}
              type="button"
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          );
        })}
      </div>

      {tab === "today" ? (
        <>
          {loadingDigest ? <LoadingState label="Loading briefing" /> : null}
          {digestError ? <ErrorState message={digestError} /> : null}
          {!loadingDigest && !digestError && digest ? (
            <div className="overflow-hidden rounded-2xl border border-[var(--line)]">
              <ExecutiveBriefingReader digest={digest} draftV1={false} />
            </div>
          ) : null}
          {!loadingDigest && !digestError && !digest ? (
            <div className="rounded-2xl border border-dashed border-[var(--line)] bg-[var(--surface)] px-6 py-12 text-center text-sm text-[var(--muted)]">
              No briefing is available yet. Generate one from the pipeline workspace, then refresh.
            </div>
          ) : null}
        </>
      ) : null}

      {tab === "history" ? <HistoryPanel /> : null}
      {tab === "bookmarks" ? <BookmarksPanel /> : null}
    </section>
  );
}
