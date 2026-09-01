"use client";

import { ResourcePage } from "@/components/resource-page";
import { StatusBadge } from "@/components/status-badge";
import { ExternalLink } from "@/components/text";
import { formatDateTime, formatScore, titleize } from "@/lib/format";
import type { Source } from "@/lib/types";

const sourceTypes = [
  "rss",
  "news_site",
  "regulator",
  "government",
  "company_ir",
  "press_release",
  "blog",
  "newsletter",
  "social",
  "youtube",
  "filing",
  "other",
];
const fetchMethods = [
  "manual",
  "rss",
  "api",
  "static_html",
  "browser",
  "newsletter",
  "filing",
  "social",
  "youtube",
];

export default function SourcesPage() {
  return (
    <ResourcePage<Source>
      columns={[
        { header: "Name", cell: (row) => row.name },
        { header: "URL", cell: (row) => <ExternalLink href={row.url} /> },
        { header: "Type", cell: (row) => titleize(row.source_type) },
        { header: "Category", cell: (row) => row.category ?? "—" },
        { header: "Region", cell: (row) => row.region ?? "—" },
        { header: "Priority", cell: (row) => row.priority },
        { header: "Method", cell: (row) => titleize(row.fetch_method) },
        { header: "Active", cell: (row) => <StatusBadge value={row.is_active} /> },
        { header: "Reliability", cell: (row) => formatScore(row.reliability_score) },
        { header: "Last Fetched", cell: (row) => formatDateTime(row.last_fetched_at) },
        { header: "Failures", cell: (row) => row.failure_count },
      ]}
      description="Source Registry records monitored by the platform."
      emptyLabel="No sources found."
      filters={[
        {
          key: "source_type",
          label: "Source Type",
          type: "select",
          options: sourceTypes.map((value) => ({ label: titleize(value), value })),
        },
        { key: "category", label: "Category" },
        { key: "region", label: "Region" },
        {
          key: "is_active",
          label: "Active",
          type: "select",
          options: [
            { label: "Active", value: "true" },
            { label: "Inactive", value: "false" },
          ],
        },
        { key: "priority", label: "Priority", type: "number" },
        {
          key: "fetch_method",
          label: "Fetch Method",
          type: "select",
          options: fetchMethods.map((value) => ({ label: titleize(value), value })),
        },
      ]}
      path="/api/v1/sources"
      title="Sources"
    />
  );
}
