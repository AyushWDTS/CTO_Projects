import {
  AlertTriangle,
  Bell,
  Cpu,
  Eye,
  Factory,
  Flag,
  Gavel,
  type LucideIcon,
  ShieldCheck,
  Sparkles,
  Table2,
  Target,
  TrendingUp,
  Workflow,
} from "lucide-react";

export const URGENCY_STYLES: Record<string, string> = {
  Immediate:
    "bg-red-100 text-red-700 ring-1 ring-red-200 dark:bg-red-500/15 dark:text-red-300 dark:ring-red-500/30",
  Discuss:
    "bg-amber-100 text-amber-700 ring-1 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-500/30",
  Monitor:
    "bg-blue-100 text-blue-700 ring-1 ring-blue-200 dark:bg-blue-500/15 dark:text-blue-300 dark:ring-blue-500/30",
  FYI: "bg-slate-100 text-slate-600 ring-1 ring-slate-200 dark:bg-slate-500/15 dark:text-slate-300 dark:ring-slate-500/30",
};

export const CATEGORY_STYLES: Record<string, string> = {
  "AI/ML":
    "bg-fuchsia-100 text-fuchsia-700 ring-1 ring-fuchsia-200 dark:bg-fuchsia-500/15 dark:text-fuchsia-300 dark:ring-fuchsia-500/30",
  "Computer Vision":
    "bg-violet-100 text-violet-700 ring-1 ring-violet-200 dark:bg-violet-500/15 dark:text-violet-300 dark:ring-violet-500/30",
  "Smart Tables":
    "bg-indigo-100 text-indigo-700 ring-1 ring-indigo-200 dark:bg-indigo-500/15 dark:text-indigo-300 dark:ring-indigo-500/30",
  Semiconductors:
    "bg-teal-100 text-teal-700 ring-1 ring-teal-200 dark:bg-teal-500/15 dark:text-teal-300 dark:ring-teal-500/30",
  Automation:
    "bg-cyan-100 text-cyan-700 ring-1 ring-cyan-200 dark:bg-cyan-500/15 dark:text-cyan-300 dark:ring-cyan-500/30",
  "Casino Tech":
    "bg-blue-100 text-blue-700 ring-1 ring-blue-200 dark:bg-blue-500/15 dark:text-blue-300 dark:ring-blue-500/30",
  Operations:
    "bg-slate-100 text-slate-700 ring-1 ring-slate-200 dark:bg-slate-500/15 dark:text-slate-300 dark:ring-slate-500/30",
  Competitor:
    "bg-red-100 text-red-700 ring-1 ring-red-200 dark:bg-red-500/15 dark:text-red-300 dark:ring-red-500/30",
  Customer:
    "bg-sky-100 text-sky-700 ring-1 ring-sky-200 dark:bg-sky-500/15 dark:text-sky-300 dark:ring-sky-500/30",
  Supplier:
    "bg-indigo-100 text-indigo-700 ring-1 ring-indigo-200 dark:bg-indigo-500/15 dark:text-indigo-300 dark:ring-indigo-500/30",
  Regulation:
    "bg-amber-100 text-amber-700 ring-1 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-500/30",
  Compliance:
    "bg-amber-100 text-amber-700 ring-1 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-300 dark:ring-amber-500/30",
};

export const CATEGORY_ICONS: Record<string, LucideIcon> = {
  "AI/ML": Sparkles,
  "Computer Vision": Eye,
  "Smart Tables": Table2,
  Semiconductors: Cpu,
  Automation: Workflow,
  "Casino Tech": Target,
  Operations: Cpu,
  Competitor: Flag,
  Customer: Target,
  Supplier: Factory,
  Regulation: Gavel,
  Compliance: ShieldCheck,
};

export const KPI_META: Record<
  string,
  { icon: LucideIcon; gradient: string; iconWrap: string }
> = {
  top: {
    icon: TrendingUp,
    gradient: "from-sky-500/10 to-blue-500/5 dark:from-sky-400/15 dark:to-blue-500/5",
    iconWrap: "bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-300",
  },
  tech: {
    icon: Cpu,
    gradient: "from-indigo-500/10 to-violet-500/5 dark:from-indigo-400/15 dark:to-violet-500/5",
    iconWrap: "bg-indigo-100 text-indigo-700 dark:bg-indigo-500/20 dark:text-indigo-300",
  },
  sales: {
    icon: Target,
    gradient: "from-emerald-500/10 to-teal-500/5 dark:from-emerald-400/15 dark:to-teal-500/5",
    iconWrap: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-300",
  },
  competitor: {
    icon: Flag,
    gradient: "from-rose-500/10 to-red-500/5 dark:from-rose-400/15 dark:to-red-500/5",
    iconWrap: "bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-300",
  },
  regulatory: {
    icon: Gavel,
    gradient: "from-amber-500/10 to-orange-500/5 dark:from-amber-400/15 dark:to-orange-500/5",
    iconWrap: "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-300",
  },
  action: {
    icon: Bell,
    gradient: "from-violet-500/10 to-purple-500/5 dark:from-violet-400/15 dark:to-purple-500/5",
    iconWrap: "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-300",
  },
};

export const SECTION_ICONS: Record<string, LucideIcon> = {
  "Top Stories": TrendingUp,
  "AI, ML & Computer Vision": Sparkles,
  "Smart Tables & Casino Tech": Table2,
  "Semiconductors & Components": Cpu,
  "Automation & Operations Tech": Workflow,
  "Competitors & Industry Watch": Flag,
  "Regulation & Compliance": Gavel,
  "Action Items": AlertTriangle,
};

export function urgencyClass(urgency: string): string {
  return URGENCY_STYLES[urgency] ?? URGENCY_STYLES.FYI;
}

export function categoryClass(category: string): string {
  return CATEGORY_STYLES[category] ?? CATEGORY_STYLES.Operations;
}
