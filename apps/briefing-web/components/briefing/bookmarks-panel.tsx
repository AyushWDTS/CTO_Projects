"use client";

import { Bookmark, CalendarDays, ExternalLink, Trash2 } from "lucide-react";
import { useBookmarks } from "@/components/briefing/bookmark-context";
import { ErrorState, LoadingState } from "@/components/state-blocks";
import { formatDate, formatDateTime } from "@/lib/format";

export function BookmarksPanel() {
  const { bookmarks, loading, error, removeBookmark, refresh } = useBookmarks();

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold tracking-tight">Bookmarks</h3>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Stories you saved from daily briefings for later review.
          </p>
        </div>
        <button
          className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-1.5 text-sm font-medium hover:bg-[var(--surface-2)]"
          onClick={() => void refresh()}
          type="button"
        >
          Refresh
        </button>
      </div>

      {loading ? <LoadingState label="Loading bookmarks" /> : null}
      {error ? <ErrorState message={error} /> : null}

      {!loading && !error && bookmarks.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[var(--line)] bg-[var(--surface)] px-6 py-12 text-center text-sm text-[var(--muted)]">
          No bookmarks yet. Open a briefing and tap the bookmark icon on a story.
        </div>
      ) : null}

      <div className="grid gap-3">
        {bookmarks.map((item) => (
          <article
            className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5"
            key={item.id}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
                  <Bookmark className="h-3.5 w-3.5 text-[var(--primary)]" />
                  {item.section ? <span>{item.section}</span> : null}
                  {item.digest_date ? (
                    <span className="inline-flex items-center gap-1">
                      <CalendarDays className="h-3.5 w-3.5" />
                      {formatDate(item.digest_date)}
                    </span>
                  ) : null}
                  {item.importance_tier ? <span className="uppercase">{item.importance_tier}</span> : null}
                </div>
                <h4 className="mt-2 text-base font-semibold text-[var(--ink)]">{item.headline}</h4>
                {item.summary ? (
                  <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">{item.summary}</p>
                ) : null}
                {item.why_it_matters ? (
                  <p className="mt-2 text-sm text-[var(--ink)]">
                    <span className="font-semibold">Why it matters:</span> {item.why_it_matters}
                  </p>
                ) : null}
                <p className="mt-3 text-xs text-[var(--muted)]">
                  Saved {formatDateTime(item.created_at)}
                </p>
              </div>
              <button
                aria-label="Remove bookmark"
                className="rounded-lg border border-[var(--line)] p-2 text-[var(--muted)] hover:bg-[var(--surface-2)] hover:text-red-600"
                onClick={() => void removeBookmark(item.id)}
                type="button"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
            {item.source_url ? (
              <a
                className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-[var(--primary)] hover:opacity-80"
                href={item.source_url}
                rel="noreferrer"
                target="_blank"
              >
                Open source
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
