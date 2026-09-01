/**
 * Read-only Executive REST paths allowed through the briefing-web BFF (v1).
 * OAuth, admin, sync POST, action-items, and decisions are excluded until approved.
 */

const UUID =
  "[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}";

const ALLOWED_PATTERNS: RegExp[] = [
  /^sync\/status$/,
  /^calendar\/today$/,
  /^calendar\/week$/,
  /^calendar\/events$/,
  /^meetings\/upcoming$/,
  new RegExp(`^meetings/${UUID}$`),
  new RegExp(`^meetings/${UUID}/brief$`),
  new RegExp(`^meetings/${UUID}/summary$`),
  /^travel\/upcoming$/,
  new RegExp(`^travel/${UUID}$`),
];

/** Returns true when path (no leading slash) is on the v1 allowlist. */
export function isExecutivePathAllowed(pathSegments: string[]): boolean {
  const path = pathSegments.filter(Boolean).join("/");
  if (!path) return false;
  if (path.startsWith("oauth/") || path.startsWith("admin/")) return false;
  if (path === "sync/gmail" || path === "sync/graph") return false;
  if (path.startsWith("action-items") || path.startsWith("decisions")) return false;
  return ALLOWED_PATTERNS.some((pattern) => pattern.test(path));
}

export const EXECUTIVE_BFF_ALLOWED_READ_PATHS = [
  "sync/status",
  "calendar/today",
  "calendar/week",
  "calendar/events",
  "meetings/*",
  "meetings/{id}",
  "meetings/{id}/brief",
  "meetings/{id}/summary",
  "travel/upcoming",
  "travel/{id}",
] as const;
