"use client";

import { useSearchParams } from "next/navigation";
import { DataTable } from "@/components/data-table";
import { FilterBar } from "@/components/filter-bar";
import { PaginationControls } from "@/components/pagination-controls";
import { PageHeader, paramsFromSearch } from "@/components/resource-page";
import { EmptyState, ErrorState, LoadingState } from "@/components/state-blocks";
import { StatusBadge } from "@/components/status-badge";
import { ExternalLink, TruncatedText } from "@/components/text";
import { useApiList } from "@/lib/api";
import { formatBytes, formatDateTime } from "@/lib/format";
import type { RawDocument, SourceFetchLog } from "@/lib/types";

export default function IngestionPage() {
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab") === "raw-documents" ? "raw-documents" : "logs";
  const filters =
    tab === "logs"
      ? [
          { key: "source_id", label: "Source ID" },
          {
            key: "status",
            label: "Status",
            type: "select" as const,
            options: ["success", "failed", "skipped"].map((value) => ({ label: value, value })),
          },
        ]
      : [{ key: "source_id", label: "Source ID" }];
  const params = paramsFromSearch(searchParams, filters.map((filter) => filter.key));
  const logs = useApiList<SourceFetchLog>("/api/v1/ingestion/logs", params);
  const docs = useApiList<RawDocument>("/api/v1/ingestion/raw-documents", params);
  const state = tab === "logs" ? logs : docs;

  return (
    <div className="space-y-5">
      <PageHeader
        description="Inspect source fetch logs and raw documents captured by ingestion."
        title="Ingestion"
      />
      <div className="flex gap-2">
        <TabLink active={tab === "logs"} href="/ingestion?tab=logs" label="Fetch Logs" />
        <TabLink
          active={tab === "raw-documents"}
          href="/ingestion?tab=raw-documents"
          label="Raw Documents"
        />
      </div>
      <FilterBar fields={filters} />
      {state.loading ? <LoadingState /> : null}
      {state.error ? <ErrorState message={state.error} /> : null}
      {!state.loading && !state.error && state.data?.items.length === 0 ? <EmptyState /> : null}
      {!state.loading && !state.error && state.data && state.data.items.length > 0 ? (
        <>
          {tab === "logs" ? (
            <DataTable
              columns={[
                { header: "Status", cell: (row) => <StatusBadge value={row.status} /> },
                { header: "Source ID", cell: (row) => <TruncatedText value={row.source_id} /> },
                { header: "HTTP", cell: (row) => row.http_status ?? "—" },
                { header: "Found", cell: (row) => row.items_found ?? "—" },
                { header: "Stored", cell: (row) => row.items_stored ?? "—" },
                { header: "Started", cell: (row) => formatDateTime(row.started_at) },
                { header: "Error", cell: (row) => <TruncatedText value={row.error_message} /> },
              ]}
              rows={state.data.items as SourceFetchLog[]}
            />
          ) : (
            <DataTable
              columns={[
                { header: "URL", cell: (row) => <ExternalLink href={row.url} /> },
                { header: "Source ID", cell: (row) => <TruncatedText value={row.source_id} /> },
                { header: "Type", cell: (row) => row.content_type ?? "—" },
                { header: "HTTP", cell: (row) => row.http_status ?? "—" },
                { header: "Size", cell: (row) => formatBytes(row.raw_size_bytes) },
                { header: "Fetched", cell: (row) => formatDateTime(row.fetched_at) },
                { header: "Hash", cell: (row) => <TruncatedText value={row.raw_hash} /> },
              ]}
              rows={state.data.items as RawDocument[]}
            />
          )}
          <PaginationControls
            limit={state.data.limit}
            offset={state.data.offset}
            total={state.data.total}
          />
        </>
      ) : null}
    </div>
  );
}

function TabLink({ active, href, label }: { active: boolean; href: string; label: string }) {
  return (
    <a
      className={`rounded-md border px-3 py-2 text-sm font-medium ${
        active ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 bg-white"
      }`}
      href={href}
    >
      {label}
    </a>
  );
}
