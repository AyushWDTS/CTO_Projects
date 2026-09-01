"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback } from "react";
import { DataTable } from "@/components/data-table";
import { MetadataDisclosure } from "@/components/metadata-disclosure";
import { RunTimeline } from "@/components/orchestration/run-timeline";
import { PageHeader } from "@/components/resource-page";
import { EmptyState, ErrorState, LoadingState } from "@/components/state-blocks";
import { StatusBadge } from "@/components/status-badge";
import { TruncatedText } from "@/components/text";
import { formatDate, formatDateTime } from "@/lib/format";
import { isTerminalRunStatus, usePolling } from "@/lib/use-polling";
import type { OrchestrationRun } from "@/lib/types";

export default function OrchestrationRunDetailPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;

  const stopWhen = useCallback(
    (payload: OrchestrationRun) => isTerminalRunStatus(payload.status),
    [],
  );

  const { data: run, error, loading } = usePolling<OrchestrationRun>(
    `/api/v1/orchestration/runs/${runId}`,
    {},
    {
      intervalMs: 10_000,
      stopWhen,
    },
  );

  const steps = run?.steps ?? [];

  return (
    <div className="space-y-5">
      <PageHeader
        description="Run metadata and per-step execution status."
        title="Orchestration Run Detail"
      />
      {loading && !run ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error && !run ? <EmptyState label="Run not found." /> : null}
      {!error && run ? (
        <>
          {run.triggered_by === "dashboard" ? (
            <p className="text-sm text-slate-600">
              Triggered from the{" "}
              <Link className="font-semibold text-sky-700 underline" href="/admin">
                admin dashboard
              </Link>
              .
            </p>
          ) : null}

          <RunTimeline run={run} steps={steps} />

          <section className="grid gap-4 rounded-md border border-slate-200 bg-white p-4 md:grid-cols-2">
            <Detail label="Status" value={<StatusBadge value={run.status} />} />
            <Detail label="Run Type" value={run.run_type} />
            <Detail label="Digest Date" value={formatDate(run.digest_date)} />
            <Detail label="Started" value={formatDateTime(run.started_at)} />
            <Detail label="Finished" value={formatDateTime(run.finished_at)} />
            <Detail label="Duration Seconds" value={run.duration_seconds ?? "—"} />
            <Detail label="Triggered By" value={run.triggered_by} />
            <Detail label="Dry Run" value={<StatusBadge value={run.dry_run} />} />
            <Detail label="Digest ID" value={<TruncatedText value={run.digest_id} />} />
            <Detail label="Error" value={<TruncatedText value={run.error_message} />} />
            <Detail label="Lock Key" value={<TruncatedText value={run.lock_key} />} />
            <Detail label="Idempotency Key" value={<TruncatedText value={run.idempotency_key} />} />
          </section>
          <MetadataDisclosure value={run.metadata} />
          <section className="space-y-3">
            <h3 className="text-lg font-semibold">Steps (table)</h3>
            {steps.length ? (
              <DataTable
                columns={[
                  { header: "Order", cell: (row) => row.step_order },
                  { header: "Step", cell: (row) => row.step_name },
                  { header: "Status", cell: (row) => <StatusBadge value={row.status} /> },
                  { header: "Processed", cell: (row) => row.items_processed ?? "—" },
                  { header: "Created", cell: (row) => row.items_created ?? "—" },
                  { header: "Failed", cell: (row) => row.items_failed ?? "—" },
                  { header: "Duration", cell: (row) => row.duration_seconds ?? "—" },
                  { header: "Error", cell: (row) => <TruncatedText value={row.error_message} /> },
                  { header: "Metadata", cell: (row) => <MetadataDisclosure value={row.metadata} /> },
                ]}
                rows={steps}
              />
            ) : (
              <EmptyState label="No run steps found." />
            )}
          </section>
        </>
      ) : null}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <div className="mt-1 text-sm text-slate-800">{value}</div>
    </div>
  );
}
