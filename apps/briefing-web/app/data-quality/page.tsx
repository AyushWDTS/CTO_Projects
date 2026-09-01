"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { DataTable } from "@/components/data-table";
import { FilterBar, type FilterField } from "@/components/filter-bar";
import { MetadataDisclosure } from "@/components/metadata-disclosure";
import { PageHeader, paramsFromSearch } from "@/components/resource-page";
import { ErrorState, LoadingState } from "@/components/state-blocks";
import { StatusBadge } from "@/components/status-badge";
import { TruncatedText } from "@/components/text";
import { PaginationControls } from "@/components/pagination-controls";
import { useApiData, useApiList } from "@/lib/api";
import { formatBytes, formatDateTime, titleize } from "@/lib/format";
import type {
  DataQualityFinding,
  DataQualitySummary,
  SourceHealthCheck,
} from "@/lib/types";

const FINDING_FILTERS: FilterField[] = [
  {
    key: "severity",
    label: "Severity",
    type: "select",
    options: ["info", "warning", "error", "critical"].map((value) => ({ label: value, value })),
  },
  {
    key: "min_severity",
    label: "Min Severity",
    type: "select",
    options: ["info", "warning", "error", "critical"].map((value) => ({ label: value, value })),
  },
  { key: "check_name", label: "Check Name" },
  {
    key: "scope_type",
    label: "Scope Type",
    type: "select",
    options: [
      "source",
      "raw_document",
      "article",
      "event",
      "analysis",
      "digest",
      "orchestration_run",
      "system",
    ].map((value) => ({ label: value, value })),
  },
  { key: "source_id", label: "Source ID" },
  { key: "run_id", label: "Run ID" },
];

const HEALTH_FILTERS: FilterField[] = [
  { key: "source_id", label: "Source ID" },
  {
    key: "status",
    label: "Status",
    type: "select",
    options: ["healthy", "degraded", "failing", "skipped"].map((value) => ({
      label: value,
      value,
    })),
  },
];

export default function DataQualityPage() {
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab") === "source-health" ? "source-health" : "findings";
  const filters = tab === "source-health" ? HEALTH_FILTERS : FINDING_FILTERS;
  const params = paramsFromSearch(searchParams, filters.map((filter) => filter.key));
  const summary = useApiData<DataQualitySummary>("/api/v1/data-quality/summary");
  const findings = useApiList<DataQualityFinding>("/api/v1/data-quality/checks", params);
  const health = useApiList<SourceHealthCheck>("/api/v1/data-quality/source-health", params);
  const activeList = tab === "source-health" ? health : findings;

  return (
    <div className="space-y-5">
      <PageHeader
        description="Read-only data quality findings and source health snapshots."
        title="Data Quality"
      />
      {summary.loading ? <LoadingState label="Loading quality summary" /> : null}
      {summary.error ? <ErrorState message={summary.error} /> : null}
      {summary.data ? <QualitySummaryCards summary={summary.data} /> : null}

      <div className="flex flex-wrap gap-2">
        <TabLink active={tab === "findings"} href="/data-quality?tab=findings" label="Findings" />
        <TabLink
          active={tab === "source-health"}
          href="/data-quality?tab=source-health"
          label="Source Health"
        />
      </div>

      <FilterBar fields={filters} />
      {activeList.loading ? <LoadingState /> : null}
      {activeList.error ? <ErrorState message={activeList.error} /> : null}
      {!activeList.loading && !activeList.error && tab === "findings" && findings.data ? (
        <>
          <DataTable
            columns={[
              { header: "Severity", cell: (row) => <StatusBadge value={row.severity} /> },
              { header: "Check", cell: (row) => titleize(row.check_name) },
              { header: "Scope", cell: (row) => row.scope_type },
              { header: "Source", cell: (row) => <TruncatedText value={row.source_id} /> },
              { header: "Message", cell: (row) => <TruncatedText value={row.message} length={96} /> },
              { header: "Recommendation", cell: (row) => <TruncatedText value={row.recommendation} /> },
              { header: "Created", cell: (row) => formatDateTime(row.created_at) },
              { header: "Metadata", cell: (row) => <MetadataDisclosure value={row.metadata} /> },
            ]}
            rows={findings.data.items}
          />
          <PaginationControls
            limit={findings.data.limit}
            offset={findings.data.offset}
            total={findings.data.total}
          />
        </>
      ) : null}
      {!activeList.loading && !activeList.error && tab === "source-health" && health.data ? (
        <>
          <DataTable
            columns={[
              { header: "Status", cell: (row) => <StatusBadge value={row.status} /> },
              { header: "Source", cell: (row) => <TruncatedText value={row.source_id} /> },
              { header: "HTTP", cell: (row) => row.http_status ?? "—" },
              { header: "Latency", cell: (row) => (row.latency_ms == null ? "—" : `${row.latency_ms} ms`) },
              { header: "Items", cell: (row) => row.item_count ?? "—" },
              { header: "Size", cell: (row) => formatBytes(row.content_size_bytes) },
              { header: "Recommendation", cell: (row) => <TruncatedText value={row.recommendation} /> },
              { header: "Checked", cell: (row) => formatDateTime(row.checked_at) },
              { header: "Metadata", cell: (row) => <MetadataDisclosure value={row.metadata} /> },
            ]}
            rows={health.data.items}
          />
          <PaginationControls limit={health.data.limit} offset={health.data.offset} total={health.data.total} />
        </>
      ) : null}
    </div>
  );
}

function QualitySummaryCards({ summary }: { summary: DataQualitySummary }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      <SummaryCard label="Latest Run" value={summary.latest_run?.status ?? "—"} />
      <SummaryCard label="Critical Findings" value={summary.severity_counts.critical ?? 0} />
      <SummaryCard label="Error Findings" value={summary.severity_counts.error ?? 0} />
      <SummaryCard label="Failing Sources" value={summary.source_health_counts.failing ?? 0} />
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-2xl font-semibold text-slate-950">{value}</p>
    </div>
  );
}

function TabLink({ active, href, label }: { active: boolean; href: string; label: string }) {
  return (
    <Link
      className={`rounded-md border px-3 py-1.5 text-sm font-medium ${
        active
          ? "border-slate-900 bg-slate-900 text-white"
          : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
      }`}
      href={href}
    >
      {label}
    </Link>
  );
}
