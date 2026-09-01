"use client";

import Link from "next/link";
import { useCallback, useMemo } from "react";
import { DataTable } from "@/components/data-table";
import { StatusBadge } from "@/components/status-badge";
import { DetailLink, TruncatedText } from "@/components/text";
import { formatDate, formatDateTime } from "@/lib/format";
import { isTerminalRunStatus, usePolling } from "@/lib/use-polling";
import type { ListResponse, OrchestrationRun } from "@/lib/types";

const ACTIVE_STATUSES = new Set(["pending", "running"]);

export function RecentRunsPanel() {
  const stopWhen = useCallback(
    (payload: ListResponse<OrchestrationRun>) =>
      payload.items.every((run) => isTerminalRunStatus(run.status)),
    [],
  );

  const { data, error, loading } = usePolling<ListResponse<OrchestrationRun>>(
    "/api/v1/orchestration/runs",
    { limit: 10, offset: 0 },
    {
      intervalMs: 10_000,
      stopWhen,
    },
  );

  const activeRun = useMemo(
    () => data?.items.find((run) => ACTIVE_STATUSES.has(run.status)) ?? null,
    [data],
  );

  return (
    <section className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5">
      <h2 className="text-lg font-semibold text-[var(--ink)]">Recent Runs</h2>
      <p className="mt-1 text-sm text-[var(--muted)]">
        Latest orchestration runs, refreshed every 10 seconds while active.
      </p>

      {activeRun ? (
        <div className="mt-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900">
          <p className="font-semibold">Active run in progress</p>
          <p className="mt-1">
            {activeRun.run_type} · started {formatDateTime(activeRun.started_at)} ·{" "}
            <StatusBadge value={activeRun.status} />
          </p>
          <Link
            className="mt-2 inline-block font-semibold underline"
            href={`/orchestration/${activeRun.id}`}
          >
            Open live timeline
          </Link>
        </div>
      ) : null}

      {error ? (
        <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      ) : null}

      {loading && !data ? (
        <p className="mt-4 text-sm text-[var(--muted)]">Loading runs…</p>
      ) : null}

      {data?.items.length ? (
        <div className="mt-4">
          <DataTable
            columns={[
              {
                header: "Run",
                cell: (row) => (
                  <DetailLink href={`/orchestration/${row.id}`} label={row.run_type} />
                ),
              },
              { header: "Status", cell: (row) => <StatusBadge value={row.status} /> },
              { header: "Date", cell: (row) => formatDate(row.digest_date) },
              { header: "Started", cell: (row) => formatDateTime(row.started_at) },
              { header: "Duration", cell: (row) => row.duration_seconds ?? "—" },
              {
                header: "Dry Run",
                cell: (row) => <StatusBadge value={row.dry_run} />,
              },
              {
                header: "Triggered By",
                cell: (row) => <TruncatedText length={24} value={row.triggered_by} />,
              },
            ]}
            rows={data.items}
          />
        </div>
      ) : !loading ? (
        <p className="mt-4 text-sm text-[var(--muted)]">No orchestration runs yet.</p>
      ) : null}
    </section>
  );
}
