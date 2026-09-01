"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

export function PaginationControls({
  total,
  limit,
  offset,
}: {
  total: number;
  limit: number;
  offset: number;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const previousOffset = Math.max(0, offset - limit);
  const nextOffset = offset + limit;

  function setOffset(value: number) {
    const params = new URLSearchParams(searchParams.toString());
    params.set("offset", String(value));
    params.set("limit", String(limit));
    router.push(`${pathname}?${params.toString()}`);
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-600">
      <span>
        Showing {total === 0 ? 0 : offset + 1}–{Math.min(offset + limit, total)} of {total}
      </span>
      <div className="flex gap-2">
        <button
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-40"
          disabled={offset <= 0}
          onClick={() => setOffset(previousOffset)}
          type="button"
        >
          Previous
        </button>
        <button
          className="rounded-md border border-slate-200 bg-white px-3 py-1.5 disabled:cursor-not-allowed disabled:opacity-40"
          disabled={nextOffset >= total}
          onClick={() => setOffset(nextOffset)}
          type="button"
        >
          Next
        </button>
      </div>
    </div>
  );
}
