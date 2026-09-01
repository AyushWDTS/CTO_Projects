"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { RunTimeline } from "@/components/orchestration/run-timeline";
import { StatusBadge } from "@/components/status-badge";
import { fetchJson, postJson } from "@/lib/api";
import { friendlyApiError, isTerminalRunStatus } from "@/lib/use-polling";
import type { ListResponse, OrchestrationRun, Source } from "@/lib/types";

type LivePipelineProps = {
  onDigestReady?: (digestId: string) => void;
};

export function LivePipeline({ onDigestReady }: LivePipelineProps) {
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [run, setRun] = useState<OrchestrationRun | null>(null);
  const [sourceCount, setSourceCount] = useState<number | null>(null);
  const pollTimer = useRef<number | null>(null);
  const postInFlight = useRef(false);
  const notifiedDigest = useRef<string | null>(null);

  const stopPolling = useCallback(() => {
    if (pollTimer.current != null) {
      window.clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  const refreshRun = useCallback(async (runId: string) => {
    const detail = await fetchJson<OrchestrationRun>(`/api/v1/orchestration/runs/${runId}`);
    setRun(detail);
    return detail;
  }, []);

  const findActiveOrLatestRun = useCallback(async (): Promise<OrchestrationRun | null> => {
    const list = await fetchJson<ListResponse<OrchestrationRun>>("/api/v1/orchestration/runs", {
      limit: 5,
      offset: 0,
    });
    const active = list.items.find((item) =>
      ["pending", "running"].includes(item.status),
    );
    return active ?? list.items[0] ?? null;
  }, []);

  const startPolling = useCallback(
    (runId: string) => {
      stopPolling();
      const tick = async () => {
        try {
          const detail = await refreshRun(runId);
          if (detail.digest_id && notifiedDigest.current !== detail.digest_id) {
            notifiedDigest.current = detail.digest_id;
            onDigestReady?.(detail.digest_id);
          }
          if (isTerminalRunStatus(detail.status)) {
            stopPolling();
            setStarting(false);
            postInFlight.current = false;
          }
        } catch (err: unknown) {
          setError(friendlyApiError(err, "Failed to refresh pipeline progress."));
        }
      };
      void tick();
      pollTimer.current = window.setInterval(() => void tick(), 1500);
    },
    [onDigestReady, refreshRun, stopPolling],
  );

  useEffect(() => () => stopPolling(), [stopPolling]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await fetchJson<ListResponse<Source>>("/api/v1/sources", {
          limit: 1,
          offset: 0,
          is_active: true,
        });
        if (!cancelled) setSourceCount(list.total);
      } catch {
        if (!cancelled) setSourceCount(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [run?.status]);

  async function handleRunPipeline() {
    if (postInFlight.current || starting) return;
    postInFlight.current = true;
    setStarting(true);
    setError(null);
    setRun(null);
    notifiedDigest.current = null;
    stopPolling();

    const knownIds = new Set<string>();
    try {
      const existing = await fetchJson<ListResponse<OrchestrationRun>>(
        "/api/v1/orchestration/runs",
        { limit: 5, offset: 0 },
      );
      existing.items.forEach((item) => knownIds.add(item.id));
    } catch {
      // Continue; discovery still works via active status.
    }

    const postPromise = postJson<{ run: OrchestrationRun }>("/api/v1/orchestration/daily/run", {
      dry_run: false,
      refresh_digest: true,
      continue_on_ai_failure: true,
      limit: 200,
      digest_limit: 15,
      triggered_by: "briefing_ui",
    });

    // Discover the run while the sync POST is still executing so the UI can show live steps.
    let discoveredId: string | null = null;
    const discoverUntil = Date.now() + 120_000;
    while (!discoveredId && Date.now() < discoverUntil) {
      try {
        const candidate = await findActiveOrLatestRun();
        if (candidate && (["pending", "running"].includes(candidate.status) || !knownIds.has(candidate.id))) {
          discoveredId = candidate.id;
          setRun(candidate);
          startPolling(candidate.id);
          break;
        }
      } catch {
        // Keep trying until the POST settles.
      }
      await sleep(1000);
    }

    try {
      const response = await postPromise;
      const finished = response.run;
      setRun(finished);
      if (finished.digest_id && notifiedDigest.current !== finished.digest_id) {
        notifiedDigest.current = finished.digest_id;
        onDigestReady?.(finished.digest_id);
      }
      if (!isTerminalRunStatus(finished.status)) {
        startPolling(finished.id);
      } else {
        stopPolling();
        // One more detail fetch to include steps.
        void refreshRun(finished.id);
      }
    } catch (err: unknown) {
      setError(friendlyApiError(err, "Failed to start pipeline."));
      stopPolling();
    } finally {
      setStarting(false);
      postInFlight.current = false;
    }
  }

  const runInProgress = Boolean(run && !isTerminalRunStatus(run.status));
  const busy = starting || runInProgress;
  const steps = run?.steps ?? [];

  return (
    <section className="space-y-4">
      <div className="rounded-2xl border border-[var(--line)] bg-[var(--surface)] p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
              Pipeline
            </p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight">Run today&apos;s briefing</h2>
            <p className="mt-1 max-w-2xl text-sm text-[var(--muted)]">
              Fetch sources, ingest articles, normalize, cluster events, run AI analysis, and build
              the digest — watch each stage update live.
            </p>
            {sourceCount != null ? (
              <p className="mt-2 text-sm text-[var(--ink)]">
                Active sources ready: <span className="font-semibold">{sourceCount}</span>
              </p>
            ) : null}
            {sourceCount === 0 ? (
              <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                No sources in the database yet. Seed them first, then run the pipeline:
                <code className="mt-1 block text-xs">
                  python -m app.scripts.seed_sources
                </code>
              </p>
            ) : null}
          </div>
          <button
            className="rounded-lg bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={busy}
            onClick={() => void handleRunPipeline()}
            type="button"
          >
            {busy ? "Pipeline running…" : "Run Pipeline"}
          </button>
        </div>

        {error ? (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        ) : null}

        {!run && busy ? (
          <p className="mt-4 flex items-center gap-2 text-sm text-[var(--muted)]">
            <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
            Starting pipeline and waiting for the first stage…
          </p>
        ) : null}

        {run ? (
          <div className="mt-5 space-y-3">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="text-[var(--muted)]">Overall status</span>
              <StatusBadge value={run.status} />
              {busy ? (
                <span className="inline-flex items-center gap-1 text-blue-700">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
                  Live
                </span>
              ) : null}
            </div>
            <RunTimeline run={run} steps={steps} />
          </div>
        ) : null}
      </div>
    </section>
  );
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}
