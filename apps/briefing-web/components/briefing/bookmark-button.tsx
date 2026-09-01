"use client";

import { Bookmark, BookmarkCheck } from "lucide-react";
import { useState } from "react";
import { useOptionalBookmarks } from "@/components/briefing/bookmark-context";
import type { BriefingItem } from "@/lib/briefing";
import type { Digest } from "@/lib/types";

export function BookmarkButton({
  item,
  digest,
}: {
  item: BriefingItem;
  digest?: Digest | null;
}) {
  const bookmarks = useOptionalBookmarks();
  const [busy, setBusy] = useState(false);

  if (!bookmarks || !digest) return null;

  const bookmarked = bookmarks.isBookmarked(item.raw.event_id);

  async function handleClick() {
    if (!bookmarks || !digest || busy) return;
    setBusy(true);
    try {
      await bookmarks.toggleBookmark(item, digest);
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      aria-label={bookmarked ? "Remove bookmark" : "Bookmark story"}
      className={`rounded-lg border p-2 transition ${
        bookmarked
          ? "border-[var(--primary)] bg-[var(--primary)]/10 text-[var(--primary)]"
          : "border-slate-200 text-slate-500 hover:border-slate-300 hover:text-slate-800 dark:border-white/10 dark:text-slate-400"
      }`}
      disabled={busy}
      onClick={() => void handleClick()}
      type="button"
    >
      {bookmarked ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}
    </button>
  );
}
