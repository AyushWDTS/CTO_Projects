"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ConfirmRunModal } from "@/components/admin/confirm-run-modal";
import { StatusBadge } from "@/components/status-badge";
import { postJson } from "@/lib/api";
import { friendlyApiError } from "@/lib/use-polling";
import type { OrchestrationRun, OrchestrationRunRequest } from "@/lib/types";

type RunPipelinePanelProps = {
  onRunStarted?: (runId: string) => void;
  compact?: boolean;
};

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

export function RunPipelinePanel({ onRunStarted, compact = false }: RunPipelinePanelProps) {
  const [digestDate, setDigestDate] = useState(todayIsoDate());
  const [dryRun, setDryRun] = useState(true);
  const [skipIngestion, setSkipIngestion] = useState(false);
  const [skipNormalization, setSkipNormalization] = useState(false);
  const [skipClustering, setSkipClustering] = useState(false);
  const [skipAi, setSkipAi] = useState(false);
  const [continueOnAiFailure, setContinueOnAiFailure] = useState(false);
  const [refreshDigest, setRefreshDigest] = useState(true);
  const [limit, setLimit] = useState(200);
  const [digestLimit, setDigestLimit] = useState(15);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeRun, setActiveRun] = useState<OrchestrationRun | null>(null);

  const needsConfirmation = !dryRun;

  function buildRequest(): OrchestrationRunRequest {
    return {
      digest_date: digestDate || null,
      dry_run: dryRun,
      skip_ingestion: skipIngestion,
      skip_normalization: skipNormalization,
      skip_clustering: skipClustering,
      skip_ai: skipAi,
      continue_on_ai_failure: continueOnAiFailure,
      refresh_digest: refreshDigest,
      limit,
      digest_limit: digestLimit,
      triggered_by: "dashboard",
    };
  }

  async function executeRun() {
    setConfirmOpen(false);
    setRunning(true);
    setError(null);
    setActiveRun(null);

    const body = buildRequest();

    try {
      const response = await postJson<{ run: OrchestrationRun }>(
        "/api/v1/orchestration/daily/run",
        body as unknown as Record<string, unknown>,
      );
      setActiveRun(response.run);
      onRunStarted?.(response.run.id);
    } catch (err: unknown) {
      setError(friendlyApiError(err, "Failed to start pipeline run."));
    } finally {
      setRunning(false);
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (running) return;
    if (needsConfirmation) {
      setConfirmOpen(true);
      return;
    }
    void executeRun();
  }

  return (
    <section className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-[var(--ink)]">Run Pipeline</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Manually exercise the full WDTS news pipeline: fetch → ingest → normalize → cluster →
            analyze → build digest.
          </p>
        </div>
        <ol className="hidden text-xs text-[var(--muted)] xl:block">
          <li>1. Fetch sources</li>
          <li>2. Ingest raw content</li>
          <li>3. Normalize articles</li>
          <li>4. Cluster events</li>
          <li>5. Run AI analysis</li>
          <li>6. Build digest</li>
        </ol>
      </div>

      <form className="mt-4 space-y-4" onSubmit={handleSubmit}>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <label className="block text-sm">
            <span className="font-medium text-[var(--ink)]">Digest date</span>
            <input
              className="mt-1 w-full rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm"
              onChange={(e) => setDigestDate(e.target.value)}
              type="date"
              value={digestDate}
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-[var(--ink)]">Item limit</span>
            <input
              className="mt-1 w-full rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm"
              max={500}
              min={1}
              onChange={(e) => setLimit(Number(e.target.value))}
              type="number"
              value={limit}
            />
          </label>
          <label className="block text-sm">
            <span className="font-medium text-[var(--ink)]">Digest limit</span>
            <input
              className="mt-1 w-full rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm"
              max={50}
              min={1}
              onChange={(e) => setDigestLimit(Number(e.target.value))}
              type="number"
              value={digestLimit}
            />
          </label>
        </div>

        <div className="flex flex-wrap gap-4 text-sm">
          <Toggle checked={dryRun} label="Dry run" onChange={setDryRun} />
          <Toggle checked={refreshDigest} label="Refresh digest" onChange={setRefreshDigest} />
          <Toggle checked={skipIngestion} label="Skip ingestion" onChange={setSkipIngestion} />
          {!compact ? (
            <>
              <Toggle
                checked={skipNormalization}
                label="Skip normalization"
                onChange={setSkipNormalization}
              />
              <Toggle
                checked={skipClustering}
                label="Skip clustering"
                onChange={setSkipClustering}
              />
              <Toggle checked={skipAi} label="Skip AI" onChange={setSkipAi} />
            </>
          ) : null}
          <Toggle
            checked={continueOnAiFailure}
            label="Continue on AI failure"
            onChange={setContinueOnAiFailure}
          />
        </div>

        {error ? (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        ) : null}

        {running ? (
          <p className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-800">
            Pipeline running… This may take several minutes. Monitor progress in Recent Runs or open
            the run timeline when it appears.
          </p>
        ) : null}

        {activeRun ? (
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
            <p>
              Run finished with status <StatusBadge value={activeRun.status} />.
              {activeRun.digest_id ? " Digest is ready to review." : ""}
            </p>
            <div className="mt-2 flex flex-wrap gap-3">
              <Link
                className="font-semibold text-emerald-900 underline"
                href={`/orchestration/${activeRun.id}`}
              >
                View run timeline
              </Link>
              {activeRun.digest_id ? (
                <Link
                  className="font-semibold text-emerald-900 underline"
                  href={`/briefing/${activeRun.digest_id}`}
                >
                  Open briefing
                </Link>
              ) : null}
            </div>
          </div>
        ) : null}

        <button
          className="rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          disabled={running}
          type="submit"
        >
          {running ? "Running…" : "Run Pipeline"}
        </button>
      </form>

      <ConfirmRunModal
        dryRun={dryRun}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => void executeRun()}
        open={confirmOpen}
      />
    </section>
  );
}

function Toggle({
  checked,
  label,
  onChange,
}: {
  checked: boolean;
  label: string;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2">
      <input checked={checked} onChange={(e) => onChange(e.target.checked)} type="checkbox" />
      <span className="text-[var(--ink)]">{label}</span>
    </label>
  );
}
