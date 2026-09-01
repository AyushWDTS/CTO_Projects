"use client";

import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { DataTable } from "@/components/data-table";
import { FilterBar } from "@/components/filter-bar";
import { MetadataDisclosure } from "@/components/metadata-disclosure";
import { PaginationControls } from "@/components/pagination-controls";
import { PageHeader, paramsFromSearch } from "@/components/resource-page";
import { EmptyState, ErrorState, LoadingState } from "@/components/state-blocks";
import { StatusBadge } from "@/components/status-badge";
import { ExternalLink, TruncatedText } from "@/components/text";
import { useApiData, useApiList } from "@/lib/api";
import { formatDate, formatDateTime, formatScore } from "@/lib/format";
import type { Digest, DigestItem } from "@/lib/types";
import { SECTION } from "@/lib/briefing";

const itemFilters = [
  {
    key: "section",
    label: "Section",
    type: "select" as const,
    options: Object.values(SECTION).map((value) => ({ label: value, value })),
  },
  {
    key: "importance_tier",
    label: "Tier",
    type: "select" as const,
    options: ["critical", "important", "monitor", "low"].map((value) => ({ label: value, value })),
  },
  { key: "min_score", label: "Min Score", type: "number" as const },
];

export default function DigestDetailPage() {
  const params = useParams<{ digestId: string }>();
  const searchParams = useSearchParams();
  const digestId = params.digestId;
  const detail = useApiData<Digest>(`/api/v1/digests/${digestId}`);
  const itemParams = paramsFromSearch(searchParams, itemFilters.map((filter) => filter.key), 100);
  const items = useApiList<DigestItem>(`/api/v1/digests/${digestId}/items`, itemParams);
  const loading = detail.loading || items.loading;
  const error = detail.error || items.error;
  const digest = detail.data;

  return (
    <div className="space-y-5">
      <PageHeader
        description="Digest metadata and ranked stories selected for the WDTS daily briefing."
        title="Digest Detail"
      />
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error && !digest ? <EmptyState label="Digest not found." /> : null}
      {!loading && !error && digest ? (
        <>
          <div className="flex flex-wrap gap-2">
            <Link
              className="rounded-md bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white shadow-sm"
              href={`/briefing/${digest.id}`}
            >
              Open Briefing Reader
            </Link>
            <Link
              className="rounded-md border border-[var(--line)] bg-[var(--surface)] px-4 py-2 text-sm font-semibold text-[var(--ink)]"
              href="/orchestration"
            >
              Run Pipeline
            </Link>
          </div>
          <section className="grid gap-4 rounded-md border border-slate-200 bg-white p-4 md:grid-cols-2">
            <Detail label="Title" value={digest.title} />
            <Detail label="Date" value={formatDate(digest.digest_date)} />
            <Detail label="Status" value={<StatusBadge value={digest.status} />} />
            <Detail
              label="Window"
              value={`${formatDateTime(digest.window_start)} – ${formatDateTime(digest.window_end)}`}
            />
            <Detail label="Candidates" value={digest.total_candidates} />
            <Detail label="Selected" value={digest.total_selected} />
            <Detail label="Critical" value={digest.critical_count} />
            <Detail label="Important" value={digest.important_count} />
          </section>
          <MetadataDisclosure value={digest.metadata} />
          <FilterBar fields={itemFilters} />
          {items.data?.items.length ? (
            <>
              <DataTable
                columns={[
                  { header: "Rank", cell: (row) => row.rank },
                  { header: "Section", cell: (row) => row.section },
                  { header: "Headline", cell: (row) => <TruncatedText value={row.headline} /> },
                  { header: "Tier", cell: (row) => row.importance_tier ?? "—" },
                  { header: "Score", cell: (row) => formatScore(row.final_score) },
                  {
                    header: "Summary",
                    cell: (row) => <TruncatedText length={100} value={row.summary} />,
                  },
                  {
                    header: "Source",
                    cell: (row) =>
                      Array.isArray(row.source_urls) ? (
                        <ExternalLink href={String(row.source_urls[0] ?? "")} />
                      ) : (
                        "—"
                      ),
                  },
                  { header: "Metadata", cell: (row) => <MetadataDisclosure value={row.metadata} /> },
                ]}
                rows={items.data.items}
              />
              <PaginationControls
                limit={items.data.limit}
                offset={items.data.offset}
                total={items.data.total}
              />
            </>
          ) : (
            <EmptyState label="No digest items found." />
          )}
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
