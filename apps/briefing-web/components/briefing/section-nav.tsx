"use client";

import { useEffect, useState } from "react";
import type { BriefingSection } from "@/lib/briefing";
import { SECTION_ICONS } from "@/lib/briefing-styles";

export function SectionNav({ sections }: { sections: BriefingSection[] }) {
  const [active, setActive] = useState(sections[0]?.id ?? "");

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: "-96px 0px -65% 0px", threshold: 0 },
    );
    sections.forEach((section) => {
      const el = document.getElementById(section.id);
      if (el) observer.observe(el);
    });
    return () => observer.disconnect();
  }, [sections]);

  function jump(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <nav
      aria-label="Briefing sections"
      className="hide-scrollbar -mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1"
    >
      {sections.map((section) => {
        const Icon = SECTION_ICONS[section.title];
        const isActive = active === section.id;
        return (
          <button
            className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold transition ${
              isActive
                ? "bg-slate-900 text-white shadow-sm dark:bg-sky-500 dark:text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
            }`}
            key={section.id}
            onClick={() => jump(section.id)}
            type="button"
          >
            {Icon ? <Icon className="h-3.5 w-3.5" /> : null}
            <span>{shortTitle(section.title)}</span>
            <span
              className={`rounded-full px-1.5 text-[10px] ${
                isActive
                  ? "bg-white/20 text-white"
                  : "bg-white text-slate-500 dark:bg-white/10 dark:text-slate-400"
              }`}
            >
              {section.count}
            </span>
          </button>
        );
      })}
    </nav>
  );
}

function shortTitle(title: string): string {
  const map: Record<string, string> = {
    "Top Stories": "Top Stories",
    "AI, ML & Computer Vision": "AI / ML / CV",
    "Smart Tables & Casino Tech": "Smart Tables",
    "Semiconductors & Components": "Semiconductors",
    "Automation & Operations Tech": "Automation",
    "Competitors & Industry Watch": "Competitors",
    "Regulation & Compliance": "Regulation",
    "Action Items": "Actions",
  };
  return map[title] ?? title;
}
