"use client";

import { ResourcePage } from "@/components/resource-page";
import { StatusBadge } from "@/components/status-badge";
import { DetailLink, TruncatedText } from "@/components/text";
import { formatDateTime, formatScore } from "@/lib/format";
import type { NewsEvent } from "@/lib/types";

export default function EventsPage() {
  return (
    <ResourcePage<NewsEvent>
      columns={[
        {
          header: "Event",
          cell: (row) => (
            <DetailLink href={`/events/${row.id}`} label={row.canonical_title || row.event_key} />
          ),
        },
        { header: "Category", cell: (row) => row.category ?? "—" },
        { header: "Region", cell: (row) => row.region ?? "—" },
        { header: "Published", cell: (row) => formatDateTime(row.published_at) },
        { header: "Articles", cell: (row) => row.article_count },
        { header: "Sources", cell: (row) => row.source_count },
        { header: "Confidence", cell: (row) => formatScore(row.confidence_score) },
        { header: "Status", cell: (row) => <StatusBadge value={row.status} /> },
        { header: "Primary Article", cell: (row) => <TruncatedText value={row.primary_article_id} /> },
      ]}
      description="Clustered news events created from normalized articles."
      emptyLabel="No events found."
      filters={[
        { key: "category", label: "Category" },
        { key: "region", label: "Region" },
        {
          key: "status",
          label: "Status",
          type: "select",
          options: ["active", "needs_review", "archived"].map((value) => ({ label: value, value })),
        },
        { key: "published_from", label: "Published From", type: "datetime-local" },
        { key: "published_to", label: "Published To", type: "datetime-local" },
        { key: "source_id", label: "Source ID" },
        { key: "min_confidence", label: "Min Confidence", type: "number" },
      ]}
      path="/api/v1/events"
      title="Events"
    />
  );
}
