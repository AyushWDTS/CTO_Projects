"use client";

import { useSearchParams } from "next/navigation";
import { DataTable, type Column } from "@/components/data-table";
import { FilterBar, type FilterField } from "@/components/filter-bar";
import { PaginationControls } from "@/components/pagination-controls";
import { EmptyState, ErrorState, LoadingState } from "@/components/state-blocks";
import { useApiList, type QueryParams } from "@/lib/api";

const DEFAULT_LIMIT = 25;

export function paramsFromSearch(
  searchParams: URLSearchParams,
  supportedFilters: string[],
  defaultLimit = DEFAULT_LIMIT,
): QueryParams {
  const params: QueryParams = {
    limit: searchParams.get("limit") ?? defaultLimit,
    offset: searchParams.get("offset") ?? 0,
  };
  supportedFilters.forEach((key) => {
    const value = searchParams.get(key);
    if (value) params[key] = value;
  });
  return params;
}

export function ResourcePage<T>({
  title,
  description,
  path,
  columns,
  filters = [],
  emptyLabel,
  defaultLimit = DEFAULT_LIMIT,
}: {
  title: string;
  description: string;
  path: string;
  columns: Column<T>[];
  filters?: FilterField[];
  emptyLabel?: string;
  defaultLimit?: number;
}) {
  const searchParams = useSearchParams();
  const supportedFilters = filters.map((filter) => filter.key);
  const params = paramsFromSearch(searchParams, supportedFilters, defaultLimit);
  const { data, error, loading } = useApiList<T>(path, params);

  return (
    <div className="space-y-5">
      <PageHeader description={description} title={title} />
      <FilterBar fields={filters} />
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error && data && data.items.length === 0 ? (
        <EmptyState label={emptyLabel} />
      ) : null}
      {!loading && !error && data && data.items.length > 0 ? (
        <>
          <DataTable columns={columns} rows={data.items} />
          <PaginationControls limit={data.limit} offset={data.offset} total={data.total} />
        </>
      ) : null}
    </div>
  );
}

export function PageHeader({ title, description }: { title: string; description: string }) {
  return (
    <div>
      <h2 className="text-2xl font-semibold text-slate-950">{title}</h2>
      <p className="mt-1 text-sm text-slate-600">{description}</p>
    </div>
  );
}
