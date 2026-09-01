"use client";

import { EmptyState, ErrorState, LoadingState } from "@/components/state-blocks";
import { executiveApi, type QueryParams } from "@/lib/executive-api";
import { useEffect, useState } from "react";

/** Phase 2 validation panel — JSON dump of a single BFF endpoint. */
export function ExecutiveDebugPanel({
  title,
  path,
  params = {},
}: {
  title: string;
  path: string;
  params?: QueryParams;
}) {
  const [data, setData] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const paramKey = JSON.stringify(params);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    executiveApi
      .fetchJson<unknown>(path, params)
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setData(null);
          setError(err instanceof Error ? err.message : "Failed to load");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [path, paramKey]);

  return (
    <section className="space-y-3">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-[var(--ink)]">{title}</h2>
        <p className="mt-1 font-mono text-xs text-[var(--muted)]">
          GET /executive/api{path}
        </p>
      </div>
      {loading ? <LoadingState label={`Loading ${title.toLowerCase()}`} /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error && data ? (
        <pre className="overflow-x-auto rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 text-xs text-[var(--ink)]">
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : null}
      {!loading && !error && !data ? <EmptyState label="No data" /> : null}
    </section>
  );
}
