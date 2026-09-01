"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, fetchJson } from "@/lib/api";

export type PollingState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
};

const TERMINAL_RUN_STATUSES = new Set([
  "success",
  "partial_success",
  "failed",
  "cancelled",
  "skipped",
]);

export function isTerminalRunStatus(status?: string | null): boolean {
  if (!status) return false;
  return TERMINAL_RUN_STATUSES.has(status);
}

export function usePolling<T>(
  path: string,
  params: Record<string, string | number | boolean | null | undefined> = {},
  options: {
    intervalMs?: number;
    enabled?: boolean;
    stopWhen?: (data: T) => boolean;
    stopOnError?: boolean;
  } = {},
): PollingState<T> {
  const { intervalMs = 10_000, enabled = true, stopWhen, stopOnError = false } = options;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const stoppedRef = useRef(false);
  const stopWhenRef = useRef(stopWhen);
  stopWhenRef.current = stopWhen;
  const paramsKey = JSON.stringify(params);

  const refresh = useCallback(async () => {
    if (!enabled || stoppedRef.current) return;
    try {
      const parsedParams = JSON.parse(paramsKey) as Record<
        string,
        string | number | boolean | null | undefined
      >;
      const payload = await fetchJson<T>(path, parsedParams);
      setData(payload);
      setError(null);
      if (stopWhenRef.current?.(payload)) {
        stoppedRef.current = true;
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Unexpected API error");
      if (stopOnError) {
        stoppedRef.current = true;
      }
    } finally {
      setLoading(false);
    }
  }, [enabled, path, paramsKey]);

  useEffect(() => {
    stoppedRef.current = false;
    setLoading(true);
    if (!enabled) {
      setLoading(false);
      return;
    }

    void refresh();
    const timer = window.setInterval(() => {
      if (!stoppedRef.current) void refresh();
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [enabled, intervalMs, refresh]);

  return { data, error, loading, refresh };
}

export function friendlyApiError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    if (err.status === 409) {
      return "Another pipeline run is already active. Wait for it to finish before starting a new one.";
    }
    return err.message;
  }
  return err instanceof Error ? err.message : fallback;
}
