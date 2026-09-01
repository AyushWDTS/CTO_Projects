"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ExecutiveBriefingReader } from "@/components/briefing/executive-briefing-reader";
import { LivePipeline } from "@/components/briefing/live-pipeline";
import { ErrorState, LoadingState } from "@/components/state-blocks";
import { fetchJson } from "@/lib/api";
import type { Digest, ListResponse } from "@/lib/types";

export default function BriefingHomePage() {
  const [digestId, setDigestId] = useState<string | null>(null);
  const [digest, setDigest] = useState<Digest | null>(null);
  const [loadingDigest, setLoadingDigest] = useState(true);
  const [digestError, setDigestError] = useState<string | null>(null);

  const loadDigest = useCallback(async (id: string) => {
    setLoadingDigest(true);
    setDigestError(null);
    try {
      const detail = await fetchJson<Digest>(`/api/v1/digests/${id}`);
      setDigest(detail);
      setDigestId(id);
    } catch (err: unknown) {
      setDigest(null);
      setDigestError(err instanceof Error ? err.message : "Failed to load briefing.");
    } finally {
      setLoadingDigest(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoadingDigest(true);
      try {
        const list = await fetchJson<ListResponse<Digest>>("/api/v1/digests", {
          limit: 1,
          offset: 0,
        });
        if (cancelled) return;
        const latest = list.items[0];
        if (latest) {
          await loadDigest(latest.id);
        } else {
          setLoadingDigest(false);
        }
      } catch (err: unknown) {
        if (cancelled) return;
        setDigestError(err instanceof Error ? err.message : "Failed to load briefing.");
        setLoadingDigest(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadDigest]);

  return (
    <div className="space-y-8">
      <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--muted)]">
        Pipeline testing workspace. For the leadership view, open{" "}
        <Link className="font-semibold text-[var(--primary)] underline" href="/cto">
          /cto
        </Link>
        .
      </div>
      <LivePipeline
        onDigestReady={(id) => {
          void loadDigest(id);
        }}
      />

      <section className="space-y-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
            Briefing
          </p>
          <h2 className="mt-1 text-xl font-semibold tracking-tight">Today&apos;s news briefing</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            {digest
              ? "Latest digest from the pipeline. Run Pipeline again to refresh."
              : "No briefing yet. Run the pipeline to generate the first digest."}
          </p>
        </div>

        {loadingDigest ? <LoadingState label="Loading briefing" /> : null}
        {digestError ? <ErrorState message={digestError} /> : null}
        {!loadingDigest && !digestError && digest ? (
          <div className="-mx-4 overflow-hidden rounded-2xl border border-[var(--line)] lg:-mx-0">
            <ExecutiveBriefingReader digest={digest} draftV1={false} />
          </div>
        ) : null}
        {!loadingDigest && !digestError && !digest && digestId == null ? (
          <div className="rounded-2xl border border-dashed border-[var(--line)] bg-[var(--surface)] px-6 py-12 text-center text-sm text-[var(--muted)]">
            Waiting for the first successful pipeline run…
          </div>
        ) : null}
      </section>
    </div>
  );
}
