import type { JsonValue } from "./types";

export function formatDateTime(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}

export function formatDate(value?: string | null): string {
  if (!value) return "—";
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(date);
}

export function formatScore(value?: string | number | null): string {
  if (value === null || value === undefined || value === "") return "—";
  const number = typeof value === "number" ? value : Number.parseFloat(value);
  if (Number.isNaN(number)) return String(value);
  return number.toFixed(3);
}

export function formatBytes(value?: number | null): string {
  if (value === null || value === undefined) return "—";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

export function truncate(value?: string | null, length = 80): string {
  if (!value) return "—";
  return value.length > length ? `${value.slice(0, length - 1)}…` : value;
}

export function titleize(value?: string | null): string {
  if (!value) return "—";
  return value
    .replace(/[_-]/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function stringifyJson(value?: JsonValue): string {
  if (value === undefined || value === null) return "";
  return JSON.stringify(value, null, 2);
}
