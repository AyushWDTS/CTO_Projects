"use client";

import { useState, useEffect } from "react";
import { PageHeader } from "@/components/resource-page";
import { RunPipelinePanel } from "@/components/admin/run-pipeline-panel";
import { RecentRunsPanel } from "@/components/admin/recent-runs-panel";

export default function AdminPage() {
  const isEnabled = process.env.NEXT_PUBLIC_ADMIN_ENABLED === "true";
  const requiredToken = process.env.NEXT_PUBLIC_ADMIN_TOKEN;

  const [hasToken, setHasToken] = useState(false);
  const [tokenInput, setTokenInput] = useState("");

  useEffect(() => {
    if (!requiredToken) {
      setHasToken(true);
    } else {
      const stored = sessionStorage.getItem("admin_token");
      if (stored === requiredToken) {
        setHasToken(true);
      }
    }
  }, [requiredToken]);

  const handleTokenSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (tokenInput === requiredToken) {
      sessionStorage.setItem("admin_token", tokenInput);
      setHasToken(true);
    } else {
      alert("Invalid token");
    }
  };

  if (!isEnabled) {
    return (
      <div className="space-y-5">
        <PageHeader description="System administration and pipeline control" title="Admin Dashboard" />
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 text-center text-amber-800">
          <p className="font-medium">Admin features are disabled in this environment.</p>
          <p className="mt-1 text-sm">Set NEXT_PUBLIC_ADMIN_ENABLED=true to enable.</p>
        </div>
      </div>
    );
  }

  if (!hasToken) {
    return (
      <div className="space-y-5">
        <PageHeader description="System administration and pipeline control" title="Admin Dashboard" />
        <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-6 max-w-md">
          <form onSubmit={handleTokenSubmit}>
            <label className="block text-sm font-medium text-[var(--ink)]">Admin Token Required</label>
            <input
              className="mt-2 w-full rounded-lg border border-[var(--line)] bg-[var(--surface-2)] px-3 py-2 text-sm text-[var(--ink)]"
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="Enter token..."
              type="password"
              value={tokenInput}
            />
            <button
              className="mt-4 w-full rounded-lg bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
              type="submit"
            >
              Unlock
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader description="System administration and pipeline control" title="Admin Dashboard" />
      
      <RunPipelinePanel />
      
      <RecentRunsPanel />
    </div>
  );
}
