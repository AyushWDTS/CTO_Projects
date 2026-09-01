"use client";

import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@wdts/ui";
import { executiveApi } from "@/lib/executive-api";

export function SectionPanel({
  path,
  title,
}: {
  path: string;
  title: string;
}) {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const payload = await executiveApi.fetchJson<Record<string, unknown>>(path);
        if (!cancelled) setData(payload);
      } catch (err: unknown) {
        if (!cancelled) {
          setData(null);
          setError(err instanceof Error ? err.message : "Failed to load");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [path]);

  return (
    <section className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h2>
        <p className="mt-1 text-sm text-slate-500">
          Data via Executive MCP REST (`/executive/api{path}`) through the local BFF.
        </p>
      </div>
      {loading ? <LoadingState label={`Loading ${title.toLowerCase()}`} /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error && !data ? <EmptyState label="No data" /> : null}
      {!loading && !error && data ? (
        <pre className="overflow-x-auto rounded-xl border border-slate-200 bg-white p-4 text-xs text-slate-700">
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : null}
    </section>
  );
}
