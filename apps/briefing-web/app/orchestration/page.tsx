"use client";

import { useState } from "react";
import { RunPipelinePanel } from "@/components/admin/run-pipeline-panel";
import { RecentRunsPanel } from "@/components/admin/recent-runs-panel";
import { ResourcePage } from "@/components/resource-page";
import { StatusBadge } from "@/components/status-badge";
import { DetailLink, TruncatedText } from "@/components/text";
import { formatDate, formatDateTime } from "@/lib/format";
import type { OrchestrationRun } from "@/lib/types";

export default function OrchestrationPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="space-y-6">
      <RunPipelinePanel onRunStarted={() => setRefreshKey((value) => value + 1)} />
      <RecentRunsPanel key={refreshKey} />
      <ResourcePage<OrchestrationRun>
        columns={[
          {
            header: "Run",
            cell: (row) => <DetailLink href={`/orchestration/${row.id}`} label={row.run_type} />,
          },
          { header: "Status", cell: (row) => <StatusBadge value={row.status} /> },
          { header: "Digest Date", cell: (row) => formatDate(row.digest_date) },
          { header: "Started", cell: (row) => formatDateTime(row.started_at) },
          { header: "Finished", cell: (row) => formatDateTime(row.finished_at) },
          { header: "Duration", cell: (row) => row.duration_seconds ?? "—" },
          { header: "Triggered By", cell: (row) => row.triggered_by },
          { header: "Dry Run", cell: (row) => <StatusBadge value={row.dry_run} /> },
          { header: "Lock", cell: (row) => <TruncatedText value={row.lock_key} /> },
        ]}
        description="Inspect past and current pipeline runs. Open a run to see step-by-step progress."
        emptyLabel="No orchestration runs found."
        filters={[
          {
            key: "run_type",
            label: "Run Type",
            type: "select",
            options: ["daily", "window", "manual"].map((value) => ({ label: value, value })),
          },
          {
            key: "status",
            label: "Status",
            type: "select",
            options: [
              "pending",
              "running",
              "success",
              "partial_success",
              "failed",
              "skipped",
              "cancelled",
            ].map((value) => ({ label: value, value })),
          },
          { key: "digest_date", label: "Digest Date", type: "date" },
          { key: "triggered_by", label: "Triggered By" },
          { key: "lock_key", label: "Lock Key" },
          { key: "idempotency_key", label: "Idempotency Key" },
          { key: "created_from", label: "Created From", type: "datetime-local" },
          { key: "created_to", label: "Created To", type: "datetime-local" },
        ]}
        path="/api/v1/orchestration/runs"
        title="Pipeline Run History"
      />
    </div>
  );
}
