"use client";

import { useExecutiveQuery } from "@/components/executive/use-executive-query";
import { EmptyState, ErrorState, LoadingState } from "@/components/state-blocks";
import type { ExecutiveSyncStatus } from "@/lib/executive/types";

export function ExecutiveSyncBanner() {
  const { data, error, loading } = useExecutiveQuery<ExecutiveSyncStatus>("/sync/status");

  if (loading || error || !data) return null;

  const hasErrors = data.errors.length > 0;
  const isStale = data.freshness === "stale";
  if (!hasErrors && !isStale) return null;

  return (
    <div
      className={`rounded-xl border px-4 py-3 text-sm ${
        isStale
          ? "border-amber-200 bg-amber-50 text-amber-900"
          : "border-orange-200 bg-orange-50 text-orange-900"
      }`}
      role="status"
    >
      <p className="font-semibold">
        {isStale ? "Executive data may be stale" : "Recent sync issues detected"}
      </p>
      <p className="mt-1 text-xs opacity-90">
        Freshness: {data.freshness}. Last successful sync:{" "}
        {data.last_successful_sync ?? "unknown"}. See repo docs/mcp_context.md for reconnect
        guidance — this UI is read-only.
      </p>
      {hasErrors ? (
        <ul className="mt-2 list-inside list-disc text-xs opacity-90">
          {data.errors.slice(0, 3).map((item) => (
            <li key={item.id}>
              {item.provider}: {item.message.slice(0, 120)}
              {item.message.length > 120 ? "…" : ""}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

export function ExecutiveSyncBannerInline() {
  const { data, loading } = useExecutiveQuery<ExecutiveSyncStatus>("/sync/status");
  if (loading || !data) return null;
  return (
    <p className="text-xs text-[var(--muted)]">
      Sync freshness: <span className="font-medium text-[var(--ink)]">{data.freshness}</span>
    </p>
  );
}
