"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, type ReactNode } from "react";

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const onCto = pathname === "/cto" || pathname.startsWith("/cto/");

  if (onCto) {
    return (
      <div className="min-h-full bg-[var(--bg)] text-[var(--ink)]">
        <Suspense
          fallback={
            <div className="px-4 py-6 text-sm text-[var(--muted)] lg:px-8">Loading…</div>
          }
        >
          {children}
        </Suspense>
      </div>
    );
  }

  return (
    <div className="min-h-full bg-[var(--bg)] text-[var(--ink)]">
      <header className="sticky top-[var(--header-h)] z-20 border-b border-[var(--line)] bg-[color-mix(in_srgb,var(--bg)_92%,transparent)] backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center px-4 py-3 lg:px-8">
          <Link className="min-w-0" href="/">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
              WDTS
            </p>
            <h1 className="truncate text-lg font-semibold tracking-tight">Pipeline Lab</h1>
          </Link>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6 lg:px-8">
        <Suspense
          fallback={
            <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-6 text-sm text-[var(--muted)]">
              Loading…
            </div>
          }
        >
          {children}
        </Suspense>
      </main>
    </div>
  );
}
