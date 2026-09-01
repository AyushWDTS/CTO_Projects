"use client";

import { useCallback, useEffect, useState } from "react";
import { ExecutiveBriefingReader } from "@/components/briefing/executive-briefing-reader";
import { ErrorState, LoadingState } from "@/components/state-blocks";
import { StatusBadge } from "@/components/status-badge";
import { fetchJson } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/format";
import type { Digest, ListResponse } from "@/lib/types";

export function HistoryPanel() {
  const [digests, setDigests] = useState<Digest[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedDigest, setSelectedDigest] = useState<Digest | null>(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadList = useCallback(async () => {
    setLoadingList(true);
    setError(null);
    try {
      const list = await fetchJson<ListResponse<Digest>>("/api/v1/digests", {
        limit: 60,
        offset: 0,
      });
      setDigests(list.items);
      if (!selectedId && list.items[0]) {
        setSelectedId(list.items[0].id);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load briefing history.");
    } finally {
      setLoadingList(false);
    }
  }, [selectedId]);

  useEffect(() => {
    void loadList();
    // Initial load only; selectedId dependency would re-fetch unnecessarily.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setSelectedDigest(null);
      return;
    }
    let cancelled = false;
    (async () => {
      setLoadingDetail(true);
      setError(null);
      try {
        const detail = await fetchJson<Digest>(`/api/v1/digests/${selectedId}`);
        if (!cancelled) setSelectedDigest(detail);
      } catch (err: unknown) {
        if (!cancelled) {
          setSelectedDigest(null);
          setError(err instanceof Error ? err.message : "Failed to load selected briefing.");
        }
      } finally {
        if (!cancelled) setLoadingDetail(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  return (
    <section className="space-y-4">
      <div>
        <h3 className="text-lg font-semibold tracking-tight">History</h3>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Browse past daily briefings by date if you missed a day.
        </p>
      </div>

      {loadingList ? <LoadingState label="Loading history" /> : null}
      {error ? <ErrorState message={error} /> : null}

      {!loadingList && digests.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[var(--line)] bg-[var(--surface)] px-6 py-12 text-center text-sm text-[var(--muted)]">
          No past briefings yet. Run the pipeline to create the first digest.
        </div>
      ) : null}

      {digests.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-[16rem_minmax(0,1fr)]">
          <aside className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-3">
            <p className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
              Briefing dates
            </p>
            <div className="flex max-h-[28rem] flex-col gap-1 overflow-y-auto">
              {digests.map((digest) => {
                const active = digest.id === selectedId;
                return (
                  <button
                    className={`rounded-xl px-3 py-2.5 text-left transition ${
                      active
                        ? "bg-[var(--primary)] text-white"
                        : "hover:bg-[var(--surface-2)] text-[var(--ink)]"
                    }`}
                    key={digest.id}
                    onClick={() => setSelectedId(digest.id)}
                    type="button"
                  >
                    <span className="block text-sm font-semibold">
                      {formatDate(digest.digest_date)}
                    </span>
                    <span
                      className={`mt-0.5 block text-xs ${active ? "text-white/80" : "text-[var(--muted)]"}`}
                    >
                      {digest.total_selected} stories · {digest.status}
                    </span>
                  </button>
                );
              })}
            </div>
          </aside>

          <div className="min-w-0 space-y-3">
            {selectedDigest ? (
              <div className="flex flex-wrap items-center gap-2 text-sm text-[var(--muted)]">
                <StatusBadge value={selectedDigest.status} />
                <span>
                  Window {formatDateTime(selectedDigest.window_start)} –{" "}
                  {formatDateTime(selectedDigest.window_end)}
                </span>
              </div>
            ) : null}
            {loadingDetail ? <LoadingState label="Loading briefing" /> : null}
            {!loadingDetail && selectedDigest ? (
              <div className="overflow-hidden rounded-2xl border border-[var(--line)]">
                <ExecutiveBriefingReader digest={selectedDigest} draftV1={false} />
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </section>
  );
}
