const DEFAULT_TIMEZONE = "Asia/Kolkata";

/** Timezone for Executive calendar queries (configurable via env). */
export function getExecutiveTimezone(): string {
  return (
    process.env.WDTS_EXECUTIVE_TIMEZONE?.trim() ||
    process.env.NEXT_PUBLIC_WDTS_EXECUTIVE_TIMEZONE?.trim() ||
    DEFAULT_TIMEZONE
  );
}

export function withExecutiveTimezone(params: Record<string, string> = {}): Record<string, string> {
  return { ...params, timezone: getExecutiveTimezone() };
}

/** Build query string for calendar endpoints using configured timezone. */
export function executiveCalendarQuery(extra: Record<string, string> = {}): Record<string, string> {
  return withExecutiveTimezone(extra);
}

/**
 * Build query string for range-based calendar endpoint.
 * 
 * Example usage:
 *   const firstDay = new Date(2026, 7, 1); // August 1, 2026
 *   const lastDay = new Date(2026, 7, 31); // August 31, 2026
 *   const params = executiveCalendarRangeQuery(firstDay, lastDay);
 *   // Returns: { startDate: "2026-08-01", endDate: "2026-08-31", timezone: "Asia/Kolkata" }
 */
export function executiveCalendarRangeQuery(
  startDate: Date,
  endDate: Date
): Record<string, string> {
  return {
    startDate: startDate.toISOString().split('T')[0], // Format as YYYY-MM-DD
    endDate: endDate.toISOString().split('T')[0],     // Format as YYYY-MM-DD
    timezone: getExecutiveTimezone(),
  };
}
