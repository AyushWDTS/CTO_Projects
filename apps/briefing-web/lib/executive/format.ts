import { formatDateTime } from "@/lib/format";

export function formatExecutiveWhen(value?: string | null): string {
  if (!value) return "—";
  return formatDateTime(value);
}

export function formatTimeOnly(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  return date.toLocaleTimeString("en-US", { 
    hour: "numeric", 
    minute: "2-digit",
    hour12: true 
  });
}

export function tripDateRange(start?: string | null, end?: string | null): string {
  if (!start && !end) return "Dates TBD";
  if (start && end) return `${formatDateTime(start)} – ${formatDateTime(end)}`;
  return formatDateTime(start ?? end);
}
