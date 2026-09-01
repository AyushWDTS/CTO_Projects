"use client";

import { Loader2 } from "lucide-react";
import { useParams, useSearchParams } from "next/navigation";
import { ExecutiveBriefingReader } from "@/components/briefing/executive-briefing-reader";
import { useApiData } from "@/lib/api";
import type { Digest } from "@/lib/types";

export default function BriefingReaderPage() {
  const params = useParams<{ digestId: string }>();
  const searchParams = useSearchParams();
  const draftV1 = searchParams.get("draft_v1") === "true";
  const { data, error, loading } = useApiData<Digest>(`/api/v1/digests/${params.digestId}`);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading briefing…
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 px-6 dark:bg-slate-950">
        <div className="max-w-md rounded-2xl border border-rose-200 bg-rose-50 px-6 py-8 text-center dark:border-rose-500/30 dark:bg-rose-500/10">
          <p className="text-sm font-semibold text-rose-700 dark:text-rose-300">
            {error || "Briefing not found."}
          </p>
        </div>
      </div>
    );
  }

  return <ExecutiveBriefingReader digest={data} draftV1={draftV1} />;
}
