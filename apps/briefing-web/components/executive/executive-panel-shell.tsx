"use client";

import { ExecutiveSyncBanner } from "@/components/executive/executive-sync-banner";

export function ExecutivePanelShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="space-y-4">
      <ExecutiveSyncBanner />
      {children}
    </div>
  );
}
