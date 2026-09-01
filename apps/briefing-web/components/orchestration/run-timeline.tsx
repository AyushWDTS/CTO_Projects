"use client";

import { StatusBadge } from "@/components/status-badge";
import { formatDateTime } from "@/lib/format";
import { isTerminalRunStatus } from "@/lib/use-polling";
import type { OrchestrationRun, OrchestrationRunStep } from "@/lib/types";

const STAGE_ORDER: { key: string; label: string }[] = [
  { key: "ingestion", label: "Fetch & Ingest Sources" },
  { key: "normalization", label: "Normalize Articles" },
  { key: "clustering", label: "Cluster Events" },
  { key: "event_analysis", label: "Run AI Analysis" },
  { key: "digest_build", label: "Build Digest" },
];

type RunTimelineProps = {
  run: OrchestrationRun;
  steps: OrchestrationRunStep[];
};

export function RunTimeline({ run, steps }: RunTimelineProps) {
  const stepByName = new Map(steps.map((step) => [step.step_name, step]));
  const orderedSteps = STAGE_ORDER.map((stage) => ({
    ...stage,
    step: stepByName.get(stage.key) ?? null,
  }));

  const completedCount = orderedSteps.filter((item) =>
    ["success", "partial_success", "skipped"].includes(item.step?.status ?? ""),
  ).length;
  const progressPct = Math.round((completedCount / STAGE_ORDER.length) * 100);
  const isLive = !isTerminalRunStatus(run.status);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Pipeline Timeline</h3>
          <p className="mt-1 text-sm text-slate-500">
            Run status: <StatusBadge value={run.status} />
            {isLive ? (
              <span className="ml-2 inline-flex items-center gap-1 text-blue-700">
                <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
                Live
              </span>
            ) : null}
          </p>
        </div>
        <div className="text-right text-sm text-slate-600">
          <p>{progressPct}% stages complete</p>
          <p className="text-xs text-slate-500">
            {formatDateTime(run.started_at)} → {formatDateTime(run.finished_at)}
          </p>
        </div>
      </div>

      <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
        <div
          className="h-full rounded-full bg-gradient-to-r from-sky-500 to-indigo-600 transition-all duration-500"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      <ol className="mt-6 space-y-0">
        {orderedSteps.map((item, index) => {
          const step = item.step;
          const status = step?.status ?? "pending";
          const isLast = index === orderedSteps.length - 1;
          return (
            <li className="relative flex gap-4 pb-6" key={item.key}>
              {!isLast ? (
                <span
                  aria-hidden
                  className={`absolute left-[15px] top-8 h-[calc(100%-8px)] w-0.5 ${connectorClass(status)}`}
                />
              ) : null}
              <span
                className={`relative z-10 mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-bold ${nodeClass(status)}`}
              >
                {index + 1}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-semibold text-slate-900">{item.label}</p>
                  <StatusBadge value={status} />
                  {status === "running" ? (
                    <span className="text-xs text-blue-600">In progress…</span>
                  ) : null}
                </div>
                {step ? (
                  <div className="mt-1 space-y-1 text-xs text-slate-600">
                    <p>
                      {formatDateTime(step.started_at)} → {formatDateTime(step.finished_at)}
                      {step.duration_seconds != null ? ` · ${step.duration_seconds}s` : ""}
                    </p>
                    <p>
                      Processed {step.items_processed ?? 0} · Created {step.items_created ?? 0}
                      {step.items_failed ? ` · Failed ${step.items_failed}` : ""}
                    </p>
                    {step.error_message ? (
                      <p className="rounded border border-red-200 bg-red-50 px-2 py-1 text-red-700">
                        {step.error_message}
                      </p>
                    ) : null}
                  </div>
                ) : (
                  <p className="mt-1 text-xs text-slate-400">Waiting to start</p>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function nodeClass(status: string): string {
  if (status === "success" || status === "partial_success") {
    return "border-emerald-500 bg-emerald-50 text-emerald-700";
  }
  if (status === "failed") return "border-red-500 bg-red-50 text-red-700";
  if (status === "running") return "border-blue-500 bg-blue-50 text-blue-700";
  if (status === "skipped") return "border-slate-300 bg-slate-100 text-slate-500";
  return "border-slate-200 bg-white text-slate-400";
}

function connectorClass(status: string): string {
  if (status === "success" || status === "partial_success") return "bg-emerald-300";
  if (status === "failed") return "bg-red-300";
  if (status === "running") return "bg-blue-300";
  return "bg-slate-200";
}
