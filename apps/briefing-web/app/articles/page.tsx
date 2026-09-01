"use client";

import { ResourcePage } from "@/components/resource-page";
import { StatusBadge } from "@/components/status-badge";
import { ExternalLink, TruncatedText } from "@/components/text";
import { formatDateTime } from "@/lib/format";
import type { Article } from "@/lib/types";

export default function ArticlesPage() {
  return (
    <ResourcePage<Article>
      columns={[
        { header: "Title", cell: (row) => <TruncatedText length={70} value={row.title} /> },
        { header: "Source URL", cell: (row) => <ExternalLink href={row.source_url} /> },
        { header: "Source ID", cell: (row) => <TruncatedText value={row.source_id} /> },
        { header: "Published", cell: (row) => formatDateTime(row.published_at) },
        { header: "Status", cell: (row) => <StatusBadge value={row.extraction_status} /> },
        { header: "Excerpt", cell: (row) => <TruncatedText length={96} value={row.excerpt} /> },
        {
          header: "Duplicate Of",
          cell: (row) => <TruncatedText value={row.duplicate_of_article_id} />,
        },
      ]}
      description="Normalized article records extracted from raw documents."
      emptyLabel="No articles found."
      filters={[
        { key: "source_id", label: "Source ID" },
        {
          key: "status",
          label: "Status",
          type: "select",
          options: ["success", "failed", "skipped", "exact_duplicate"].map((value) => ({
            label: value,
            value,
          })),
        },
        { key: "category", label: "Category" },
        { key: "region", label: "Region" },
        { key: "published_from", label: "Published From", type: "datetime-local" },
        { key: "published_to", label: "Published To", type: "datetime-local" },
        { key: "content_type", label: "Content Type" },
      ]}
      path="/api/v1/articles"
      title="Articles"
    />
  );
}
