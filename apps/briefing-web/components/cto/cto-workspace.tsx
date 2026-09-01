"use client";

import { ArrowUpRight, Menu, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { DailyBriefingView } from "@/components/briefing/daily-briefing-view";
import { ExecutiveCalendarPanel } from "@/components/executive/executive-calendar-panel";
import { ExecutiveMeetingsPanel } from "@/components/executive/executive-meetings-panel";
import { ExecutiveTodayPanel } from "@/components/executive/executive-today-panel";
import { ExecutiveTravelPanel } from "@/components/executive/executive-travel-panel";

export type CtoTabId =
  | "daily-briefing"
  | "executive-today"
  | "executive-calendar"
  | "executive-meetings"
  | "executive-travel"
  | "cto-dashboard"
  | "ai-dashboard";

const EXTERNAL_LINKS = {
  "cto-dashboard": "https://cto-dashboard.aiwdts.com",
  "ai-dashboard": "https://ai-dashboard.aiwdts.com",
} as const;

const TABS: {
  id: CtoTabId;
  label: string;
  description: string;
  external?: boolean;
}[] = [
  {
    id: "daily-briefing",
    label: "Daily Briefing",
    description: "WDTS daily news briefing",
  },
  {
    id: "executive-today",
    label: "Today",
    description: "Agenda and sync overview",
  },
  {
    id: "executive-calendar",
    label: "Calendar",
    description: "Today and week view",
  },
  {
    id: "executive-meetings",
    label: "Meetings",
    description: "Upcoming meetings",
  },
  {
    id: "executive-travel",
    label: "Travel",
    description: "Upcoming trips",
  },
  {
    id: "cto-dashboard",
    label: "CTO Dashboard",
    description: "Leadership ops dashboard",
    external: true,
  },
  {
    id: "ai-dashboard",
    label: "AI Dashboard",
    description: "AI platform insights",
    external: true,
  },
];

export function CtoWorkspace({ initialTab = "daily-briefing" }: { initialTab?: CtoTabId }) {
  const [activeTab, setActiveTab] = useState<CtoTabId>(initialTab);
  const [menuOpen, setMenuOpen] = useState(false);

  const activeLabel =
    TABS.find((tab) => tab.id === activeTab && !tab.external)?.label ?? "Daily Briefing";

  useEffect(() => {
    if (!menuOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [menuOpen]);

  useEffect(() => {
    const media = window.matchMedia("(min-width: 1024px)");
    const onChange = () => {
      if (media.matches) setMenuOpen(false);
    };
    onChange();
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  const panel = useMemo(() => {
    switch (activeTab) {
      case "executive-today":
        return <ExecutiveTodayPanel />;
      case "executive-calendar":
        return <ExecutiveCalendarPanel />;
      case "executive-meetings":
        return <ExecutiveMeetingsPanel />;
      case "executive-travel":
        return <ExecutiveTravelPanel />;
      case "daily-briefing":
      default:
        return (
          <DailyBriefingView helperText="Executive daily news briefing for WDTS leadership." />
        );
    }
  }, [activeTab]);

  function handleNavClick(tab: (typeof TABS)[number]) {
    if (tab.external) {
      const href = EXTERNAL_LINKS[tab.id as keyof typeof EXTERNAL_LINKS];
      window.open(href, "_blank", "noopener,noreferrer");
      setMenuOpen(false);
      return;
    }
    setActiveTab(tab.id);
    setMenuOpen(false);
  }

  return (
    <div className="relative min-h-[calc(100vh-var(--header-h))] lg:flex">
      <div className="sticky top-[var(--header-h)] z-30 border-b border-[var(--line)] bg-[var(--surface)] lg:hidden">
        <div className="flex items-center gap-3 px-4 py-3">
          <button
            aria-controls="cto-nav-drawer"
            aria-expanded={menuOpen}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--line)] bg-[var(--bg)] text-[var(--ink)] hover:bg-[var(--surface-2)]"
            onClick={() => setMenuOpen((open) => !open)}
            type="button"
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
          <div className="min-w-0">
            <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
              WDTS
            </p>
            <h1 className="truncate text-lg font-semibold tracking-tight">{activeLabel}</h1>
          </div>
        </div>
      </div>

      {menuOpen ? (
        <button
          aria-label="Close menu overlay"
          className="fixed inset-0 z-40 bg-black/35 lg:hidden"
          onClick={() => setMenuOpen(false)}
          type="button"
        />
      ) : null}

      <aside
        className={`z-50 flex w-[min(18rem,88vw)] shrink-0 flex-col border-r border-[var(--line)] bg-[var(--sidebar,var(--surface))] transition-transform duration-200 lg:static lg:translate-x-0 lg:shadow-none ${
          menuOpen
            ? "fixed bottom-0 left-0 top-[var(--header-h)] translate-x-0 shadow-xl"
            : "fixed bottom-0 left-0 top-[var(--header-h)] -translate-x-full lg:translate-x-0"
        }`}
        id="cto-nav-drawer"
      >
        <div className="border-b border-[var(--line)] px-4 py-5">
          <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
            WDTS
          </p>
          <p className="mt-1 text-base font-semibold tracking-tight text-[var(--ink)]">
            CTO Dashboard
          </p>
          <p className="mt-1 text-xs text-[var(--muted)]">Leadership workspace</p>
        </div>
        <nav aria-label="CTO dashboard sections" className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
          {TABS.map((tab) => {
            const active = !tab.external && tab.id === activeTab;
            return (
              <button
                className={`rounded-xl px-3 py-3 text-left transition ${
                  active
                    ? "bg-[var(--primary)] text-white"
                    : "text-[var(--ink)] hover:bg-[var(--surface-2)]"
                }`}
                key={tab.id}
                onClick={() => handleNavClick(tab)}
                type="button"
              >
                <span className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold">{tab.label}</span>
                  {tab.external ? (
                    <ArrowUpRight
                      aria-hidden
                      className="h-4 w-4 shrink-0 text-[var(--muted)]"
                    />
                  ) : null}
                </span>
                <span
                  className={`mt-0.5 block text-xs ${active ? "text-white/80" : "text-[var(--muted)]"}`}
                >
                  {tab.description}
                </span>
              </button>
            );
          })}
        </nav>
      </aside>

      <main className="min-w-0 flex-1 px-4 py-6 lg:px-8">{panel}</main>
    </div>
  );
}
