"use client";

import { useParams } from "next/navigation";
import { DataTable } from "@/components/data-table";
import { MetadataDisclosure } from "@/components/metadata-disclosure";
import { PageHeader } from "@/components/resource-page";
import { EmptyState, ErrorState, LoadingState } from "@/components/state-blocks";
import { StatusBadge } from "@/components/status-badge";
import { ExternalLink, TruncatedText } from "@/components/text";
import { useApiData, useApiList } from "@/lib/api";
import { formatDateTime, formatScore } from "@/lib/format";
import type { EventArticle, NewsEvent } from "@/lib/types";

export default function EventDetailPage() {
  const params = useParams<{ eventId: string }>();
  const eventId = params.eventId;
  const eventState = useApiData<NewsEvent>(`/api/v1/events/${eventId}`);
  const articleState = useApiList<EventArticle>(`/api/v1/events/${eventId}/articles`, {
    limit: 100,
    offset: 0,
  });
  const loading = eventState.loading || articleState.loading;
  const error = eventState.error || articleState.error;
  const event = eventState.data;

  return (
    <div className="space-y-5">
      <PageHeader
        description="Event details and article matches for a clustered news event."
        title="Event Detail"
      />
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error && !event ? <EmptyState label="Event not found." /> : null}
      {!loading && !error && event ? (
        <>
          <section className="grid gap-4 rounded-md border border-slate-200 bg-white p-4 md:grid-cols-2">
            <Detail label="Title" value={event.canonical_title ?? "—"} />
            <Detail label="Status" value={<StatusBadge value={event.status} />} />
            <Detail label="Canonical URL" value={<ExternalLink href={event.canonical_url} />} />
            <Detail label="Published" value={formatDateTime(event.published_at)} />
            <Detail label="Category" value={event.category ?? "—"} />
            <Detail label="Region" value={event.region ?? "—"} />
            <Detail label="Article Count" value={event.article_count} />
            <Detail label="Source Count" value={event.source_count} />
            <Detail label="Confidence" value={formatScore(event.confidence_score)} />
            <Detail label="Primary Article" value={<TruncatedText value={event.primary_article_id} />} />
          </section>
          <MetadataDisclosure value={event.metadata} />
          <section className="space-y-3">
            <h3 className="text-lg font-semibold">Linked Articles</h3>
            {articleState.data?.items.length ? (
              <DataTable
                columns={[
                  { header: "Article ID", cell: (row) => <TruncatedText value={row.article_id} /> },
                  { header: "Source ID", cell: (row) => <TruncatedText value={row.source_id} /> },
                  { header: "Match", cell: (row) => row.match_type },
                  { header: "Similarity", cell: (row) => formatScore(row.similarity_score) },
                  { header: "Confidence", cell: (row) => formatScore(row.confidence_score) },
                  { header: "Primary", cell: (row) => <StatusBadge value={row.is_primary} /> },
                  {
                    header: "Details",
                    cell: (row) => <MetadataDisclosure label="Match details" value={row.match_details} />,
                  },
                ]}
                rows={articleState.data.items}
              />
            ) : (
              <EmptyState label="No linked articles found." />
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
