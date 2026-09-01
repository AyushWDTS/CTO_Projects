"use client";

import { useEffect, useMemo, useState } from "react";

export type QueryValue = string | number | boolean | null | undefined;
export type QueryParams = Record<string, QueryValue>;

export type ListResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.replace(/\/$/, "");
}

export function joinApiUrl(baseUrl: string, path: string): string {
  const base = normalizeBaseUrl(baseUrl);
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (base.startsWith("http://") || base.startsWith("https://")) {
    const baseWithSlash = `${base}/`;
    const relative = normalizedPath.replace(/^\//, "");
    return new URL(relative, baseWithSlash).toString().split("?")[0];
  }

  if (!base) {
    return normalizedPath;
  }

  if (normalizedPath === "/") {
    return base || "/";
  }

  return `${base}${normalizedPath}`;
}

function applyQueryParams(urlString: string, params: QueryParams): string {
  const isAbsolute = urlString.startsWith("http://") || urlString.startsWith("https://");
  const url = isAbsolute
    ? new URL(urlString)
    : new URL(urlString, "http://localhost");

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    url.searchParams.set(key, String(value));
  });

  if (isAbsolute) {
    return url.toString();
  }

  return `${url.pathname}${url.search}`;
}

export type ApiClient = {
  baseUrl: string;
  buildApiUrl: (path: string, params?: QueryParams) => string;
  fetchJson: <T>(path: string, params?: QueryParams) => Promise<T>;
  postJson: <T>(path: string, body: Record<string, unknown>, params?: QueryParams) => Promise<T>;
  deleteJson: (path: string, params?: QueryParams) => Promise<void>;
};

async function readErrorMessage(response: Response): Promise<string> {
  let message = `Request failed with status ${response.status}`;
  try {
    const payload = await response.json();
    if (payload?.detail) {
      message = typeof payload.detail === "string" ? payload.detail : JSON.stringify(payload.detail);
    }
  } catch {
    // Keep the generic message when the response is not JSON.
  }
  return message;
}

export function createApiClient(options: { baseUrl: string }): ApiClient {
  const baseUrl = normalizeBaseUrl(options.baseUrl);

  function buildApiUrl(path: string, params: QueryParams = {}): string {
    return applyQueryParams(joinApiUrl(baseUrl, path), params);
  }

  async function fetchJson<T>(path: string, params: QueryParams = {}): Promise<T> {
    const response = await fetch(buildApiUrl(path, params), {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      throw new ApiError(await readErrorMessage(response), response.status);
    }
    return response.json() as Promise<T>;
  }

  async function postJson<T>(
    path: string,
    body: Record<string, unknown>,
    params: QueryParams = {},
  ): Promise<T> {
    const response = await fetch(buildApiUrl(path, params), {
      body: JSON.stringify(body),
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      method: "POST",
    });
    if (!response.ok) {
      throw new ApiError(await readErrorMessage(response), response.status);
    }
    return response.json() as Promise<T>;
  }

  async function deleteJson(path: string, params: QueryParams = {}): Promise<void> {
    const response = await fetch(buildApiUrl(path, params), {
      headers: { Accept: "application/json" },
      method: "DELETE",
    });
    if (!response.ok) {
      throw new ApiError(await readErrorMessage(response), response.status);
    }
  }

  return { baseUrl, buildApiUrl, fetchJson, postJson, deleteJson };
}

const defaultBaseUrl =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "")) ||
  "http://localhost:8000";

const defaultClient = createApiClient({ baseUrl: defaultBaseUrl });

export const API_BASE_URL = defaultClient.baseUrl;
export const buildApiUrl = defaultClient.buildApiUrl;
export const fetchJson = defaultClient.fetchJson;
export const postJson = defaultClient.postJson;
export const deleteJson = defaultClient.deleteJson;

export type AsyncState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
};

export function useApiData<T>(
  path: string,
  params: QueryParams = {},
  client: ApiClient = defaultClient,
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const key = useMemo(() => JSON.stringify(params), [params]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    fetch(client.buildApiUrl(path, params), {
      headers: { Accept: "application/json" },
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new ApiError(await readErrorMessage(response), response.status);
        }
        return response.json() as Promise<T>;
      })
      .then((payload) => {
        setData(payload);
        setError(null);
      })
      .catch((err: unknown) => {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setData(null);
        setError(err instanceof Error ? err.message : "Unexpected API error");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
    // key keeps dependency tracking stable without deep object comparisons.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, key, client]);

  return { data, error, loading };
}

export function useApiList<T>(
  path: string,
  params: QueryParams = {},
  client: ApiClient = defaultClient,
): AsyncState<ListResponse<T>> {
  return useApiData<ListResponse<T>>(path, params, client);
}
