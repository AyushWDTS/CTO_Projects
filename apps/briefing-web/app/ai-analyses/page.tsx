"use client";

import { ResourcePage } from "@/components/resource-page";
import { StatusBadge } from "@/components/status-badge";
import { TruncatedText } from "@/components/text";
import { formatDateTime, formatScore } from "@/lib/format";
import type { EventAIAnalysis } from "@/lib/types";

export default function AIAnalysesPage() {
  return (
    <ResourcePage<EventAIAnalysis>
      columns={[
        { header: "Event ID", cell: (row) => <TruncatedText value={row.event_id} /> },
        { header: "Summary", cell: (row) => <TruncatedText length={100} value={row.summary} /> },
        { header: "Tier", cell: (row) => row.importance_tier ?? "—" },
        { header: "Relevance", cell: (row) => formatScore(row.relevance_score) },
        { header: "Urgency", cell: (row) => formatScore(row.urgency_score) },
        { header: "Confidence", cell: (row) => formatScore(row.confidence_score) },
        { header: "Status", cell: (row) => <StatusBadge value={row.status} /> },
        { header: "Error", cell: (row) => <TruncatedText value={row.error_message} /> },
        { header: "Updated", cell: (row) => formatDateTime(row.updated_at) },
      ]}
      description="Event-level AI summaries and WDTS relevance scoring."
      emptyLabel="No AI analyses found."
      filters={[
        {
          key: "status",
          label: "Status",
          type: "select",
          options: ["pending", "success", "failed", "skipped"].map((value) => ({ label: value, value })),
        },
        {
          key: "importance_tier",
          label: "Tier",
          type: "select",
          options: ["critical", "important", "monitor", "low"].map((value) => ({
            label: value,
            value,
          })),
        },
        { key: "min_relevance_score", label: "Min Relevance", type: "number" },
        { key: "min_urgency_score", label: "Min Urgency", type: "number" },
        { key: "source_id", label: "Source ID" },
        { key: "category", label: "Category" },
        { key: "region", label: "Region" },
        { key: "created_from", label: "Created From", type: "datetime-local" },
        { key: "created_to", label: "Created To", type: "datetime-local" },
      ]}
      path="/api/v1/event-analysis"
      title="AI Analyses"
    />
  );
}
