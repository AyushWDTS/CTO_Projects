import { titleize } from "./titleize";

const green = new Set(["active", "success", "sent", "connected", "healthy"]);
const red = new Set(["failed", "error", "critical", "failing"]);
const amber = new Set(["partial_success", "needs_review", "warning", "degraded"]);
const blue = new Set(["running", "pending", "rendered", "draft"]);

export function StatusBadge({ value }: { value?: string | boolean | null }) {
  const normalized = String(value ?? "unknown");
  let className = "border-slate-200 bg-slate-100 text-slate-700";
  if (green.has(normalized)) className = "border-emerald-200 bg-emerald-50 text-emerald-700";
  if (red.has(normalized)) className = "border-red-200 bg-red-50 text-red-700";
  if (amber.has(normalized)) className = "border-amber-200 bg-amber-50 text-amber-800";
  if (blue.has(normalized)) className = "border-blue-200 bg-blue-50 text-blue-700";
  if (normalized === "false" || normalized === "skipped" || normalized === "archived") {
    className = "border-slate-200 bg-slate-100 text-slate-600";
  }

  return (
    <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${className}`}>
      {typeof value === "boolean" ? (value ? "Active" : "Inactive") : titleize(normalized)}
    </span>
  );
}
