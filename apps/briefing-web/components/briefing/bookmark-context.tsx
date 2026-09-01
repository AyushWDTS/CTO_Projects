"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { deleteJson, fetchJson, postJson } from "@/lib/api";
import type { BriefingItem } from "@/lib/briefing";
import type { BriefingBookmark, Digest, ListResponse } from "@/lib/types";

const USER_KEY = "default";

type BookmarkContextValue = {
  bookmarkedEventIds: Set<string>;
  bookmarks: BriefingBookmark[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  isBookmarked: (eventId: string) => boolean;
  toggleBookmark: (item: BriefingItem, digest: Digest) => Promise<void>;
  removeBookmark: (bookmarkId: string) => Promise<void>;
};

const BookmarkContext = createContext<BookmarkContextValue | null>(null);

export function BookmarkProvider({ children }: { children: ReactNode }) {
  const [bookmarks, setBookmarks] = useState<BriefingBookmark[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const list = await fetchJson<ListResponse<BriefingBookmark>>("/api/v1/bookmarks", {
        user_key: USER_KEY,
        limit: 200,
        offset: 0,
      });
      setBookmarks(list.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load bookmarks.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const bookmarkedEventIds = useMemo(
    () => new Set(bookmarks.map((item) => item.event_id)),
    [bookmarks],
  );

  const isBookmarked = useCallback(
    (eventId: string) => bookmarkedEventIds.has(eventId),
    [bookmarkedEventIds],
  );

  const toggleBookmark = useCallback(
    async (item: BriefingItem, digest: Digest) => {
      const eventId = item.raw.event_id;
      if (bookmarkedEventIds.has(eventId)) {
        await deleteJson(`/api/v1/bookmarks/by-event/${eventId}`, { user_key: USER_KEY });
        setBookmarks((prev) => prev.filter((row) => row.event_id !== eventId));
        return;
      }

      const created = await postJson<BriefingBookmark>("/api/v1/bookmarks", {
        user_key: USER_KEY,
        event_id: eventId,
        digest_id: digest.id,
        digest_item_id: item.raw.id,
        digest_date: digest.digest_date,
        section: item.meta.section || item.raw.section,
        headline: item.headline,
        summary: item.summary || null,
        why_it_matters: item.whyItMatters || null,
        suggested_action: item.suggestedAction || null,
        source_url: item.sourceUrl,
        importance_tier: item.tier || item.raw.importance_tier || null,
        metadata: {
          category: item.meta.category,
          urgency: item.meta.urgency,
          owner: item.meta.owner,
        },
      });
      setBookmarks((prev) => [created, ...prev.filter((row) => row.event_id !== eventId)]);
    },
    [bookmarkedEventIds],
  );

  const removeBookmark = useCallback(async (bookmarkId: string) => {
    await deleteJson(`/api/v1/bookmarks/${bookmarkId}`, { user_key: USER_KEY });
    setBookmarks((prev) => prev.filter((row) => row.id !== bookmarkId));
  }, []);

  const value = useMemo(
    () => ({
      bookmarkedEventIds,
      bookmarks,
      loading,
      error,
      refresh,
      isBookmarked,
      toggleBookmark,
      removeBookmark,
    }),
    [
      bookmarkedEventIds,
      bookmarks,
      loading,
      error,
      refresh,
      isBookmarked,
      toggleBookmark,
      removeBookmark,
    ],
  );

  return <BookmarkContext.Provider value={value}>{children}</BookmarkContext.Provider>;
}

export function useBookmarks() {
  const value = useContext(BookmarkContext);
  if (!value) {
    throw new Error("useBookmarks must be used within BookmarkProvider");
  }
  return value;
}

export function useOptionalBookmarks() {
  return useContext(BookmarkContext);
}
