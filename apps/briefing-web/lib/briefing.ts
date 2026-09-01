import type { Digest, DigestItem, JsonValue } from "./types";

export const SECTION = {
  TOP_STORIES: "Top Stories",
  AI_ML_CV: "AI, ML & Computer Vision",
  SMART_TABLES: "Smart Tables & Casino Tech",
  SEMICONDUCTORS: "Semiconductors & Components",
  AUTOMATION: "Automation & Operations Tech",
  COMPETITORS: "Competitors & Industry Watch",
  REGULATION: "Regulation & Compliance",
  ACTION_ITEMS: "Action Items",
} as const;

const CONTENT_SECTION_ORDER = [
  SECTION.AI_ML_CV,
  SECTION.SMART_TABLES,
  SECTION.SEMICONDUCTORS,
  SECTION.AUTOMATION,
  SECTION.COMPETITORS,
  SECTION.REGULATION,
];

const ALWAYS_SHOW = new Set<string>([
  SECTION.AI_ML_CV,
  SECTION.SMART_TABLES,
  SECTION.SEMICONDUCTORS,
  SECTION.COMPETITORS,
]);

const TOP_STORIES_LIMIT = 5;
const CONTENT_SECTION_LIMIT = 5;
const ACTION_ITEMS_LIMIT = 5;

const SUMMARY_MAX = 2;
const WHY_MAX = 2;
const ACTION_MAX = 1;
const NON_ACTIONABLE_SUGGESTIONS = new Set(["", "no action"]);

const LEGACY_SECTION_MAP: Record<string, string> = {
  "Top 5 Things Mike Should Know Today": SECTION.TOP_STORIES,
  "Brick-and-Mortar Gaming Markets": SECTION.SMART_TABLES,
  "Smart Table Games": SECTION.SMART_TABLES,
  "WDTS Operating Markets": SECTION.AUTOMATION,
  "Manufacturing and Component Supply": SECTION.SEMICONDUCTORS,
  "Finance, Tax, Tariffs, and Accounting": SECTION.SEMICONDUCTORS,
  "HR and Labor Law": SECTION.AUTOMATION,
  "Customer / Competitor / Supplier Watchlist": SECTION.COMPETITORS,
  "Action Items / Watch Items": SECTION.ACTION_ITEMS,
};

export function isActionableSuggestion(value: string | null | undefined): boolean {
  if (!value) return false;
  return !NON_ACTIONABLE_SUGGESTIONS.has(value.trim().toLowerCase());
}

export function resolveSuggestedAction(
  suggestedAction: string | null | undefined,
  actionBucket: string | null | undefined,
  maxSentences = ACTION_MAX,
): string {
  for (const candidate of [suggestedAction, actionBucket]) {
    if (!candidate) continue;
    const text = limitSentences(candidate, maxSentences);
    if (isActionableSuggestion(text)) return text;
  }
  return "";
}

export type StoryMeta = {
  section?: string;
  category: string;
  region: string;
  urgency: string;
  owner: string;
  actionBucket?: string;
  whyItMatters?: string;
  sourceName?: string;
  eventDate?: string;
  signalType?: string;
  salesOpportunitySignal?: boolean;
  isCompetitorSignal?: boolean;
};

/** @deprecated Prefer StoryMeta */
export type CooMeta = StoryMeta;

export type BriefingItem = {
  raw: DigestItem;
  rank: number;
  tier: string;
  headline: string;
  meta: StoryMeta;
  summary: string;
  whyItMatters: string;
  suggestedAction: string;
  sourceUrl: string | null;
};

export type RegionGroup = { region: string; items: BriefingItem[] };

export type BriefingSection = {
  id: string;
  title: string;
  featured: boolean;
  isActionList: boolean;
  items: BriefingItem[];
  regions: RegionGroup[] | null;
  count: number;
};

export type KpiMetric = {
  key: string;
  label: string;
  value: number;
};

export type Briefing = {
  dateLabel: string;
  windowLabel: string;
  generatedLabel: string;
  totalItems: number;
  sections: BriefingSection[];
  kpis: KpiMetric[];
};

function asRecord(value: JsonValue | undefined | null): Record<string, JsonValue> {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return value as Record<string, JsonValue>;
  }
  return {};
}

function str(value: JsonValue | undefined, fallback = ""): string {
  if (typeof value === "string") return value;
  if (typeof value === "number") return String(value);
  return fallback;
}

export function limitSentences(value: string | null | undefined, max: number): string {
  if (!value || max <= 0) return "";
  const normalized = value.replace(/\s+/g, " ").trim();
  if (!normalized) return "";
  const parts = normalized.match(/[^.!?]+[.!?]*/g);
  if (!parts) return normalized;
  const trimmed = parts.map((part) => part.trim()).filter(Boolean);
  if (trimmed.length <= max) return trimmed.join(" ");
  return trimmed.slice(0, max).join(" ");
}

function normalizeTextForCompare(value: string | null | undefined): string {
  if (!value) return "";
  return value
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase()
    .replace(/[^\w\s]/g, "");
}

function summariesMatch(headline: string | null | undefined, summary: string | null | undefined): boolean {
  const headlineNorm = normalizeTextForCompare(headline);
  const summaryNorm = normalizeTextForCompare(summary);
  if (!headlineNorm || !summaryNorm) return false;
  return headlineNorm === summaryNorm;
}

function distinctSummary(
  headline: string | null | undefined,
  summary: string | null | undefined,
  fallback?: string | null,
): string {
  const candidate = summariesMatch(headline, summary)
    ? (fallback || "").trim()
    : (summary || "").trim();
  if (!candidate) return "";
  return limitSentences(candidate, SUMMARY_MAX);
}

function normalizeSectionTitle(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return "";
  if (CONTENT_SECTION_ORDER.includes(trimmed as (typeof CONTENT_SECTION_ORDER)[number])) {
    return trimmed;
  }
  if (trimmed === SECTION.TOP_STORIES || trimmed === SECTION.ACTION_ITEMS) return trimmed;
  return LEGACY_SECTION_MAP[trimmed] ?? trimmed;
}

function readMeta(item: DigestItem): StoryMeta {
  const metadata = asRecord(item.metadata);
  const briefing = asRecord(metadata.briefing);
  const coo = asRecord(metadata.coo_briefing);
  const source = Object.keys(briefing).length ? briefing : Object.keys(coo).length ? coo : metadata;
  const sectionRaw =
    str(source.briefing_section) ||
    str(source.coo_section) ||
    str(metadata.briefing_section) ||
    str(metadata.coo_section);
  return {
    section: sectionRaw ? normalizeSectionTitle(sectionRaw) : undefined,
    category:
      str(source.briefing_category) ||
      str(source.coo_category) ||
      str(source.category) ||
      str(metadata.briefing_category) ||
      str(metadata.coo_category) ||
      "Operations",
    region: str(source.country_or_region, "Global") || str(metadata.country_or_region, "Global"),
    urgency: str(source.urgency, "FYI") || str(metadata.urgency, "FYI"),
    owner:
      str(source.suggested_owner, "Executive Team") ||
      str(metadata.suggested_owner, "Executive Team"),
    actionBucket: str(source.action_bucket) || str(metadata.action_bucket) || undefined,
    whyItMatters:
      str(source.why_it_matters_to_wdts) || str(metadata.why_it_matters_to_wdts) || undefined,
    sourceName: str(source.source_name) || str(metadata.source_name) || undefined,
    eventDate: str(source.event_date) || str(metadata.event_date) || undefined,
    signalType: str(source.signal_type) || str(metadata.signal_type) || undefined,
    salesOpportunitySignal:
      source.sales_opportunity_signal === true || metadata.sales_opportunity_signal === true,
    isCompetitorSignal:
      source.is_competitor_signal === true || metadata.is_competitor_signal === true,
  };
}

function firstUrl(item: DigestItem): string | null {
  if (!Array.isArray(item.source_urls)) return null;
  for (const value of item.source_urls) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function toBriefingItem(item: DigestItem): BriefingItem {
  const meta = readMeta(item);
  const whySource = meta.whyItMatters || item.why_it_matters || "";
  const headline = item.headline || "Untitled item";
  return {
    raw: item,
    rank: item.rank,
    tier: (item.importance_tier || "monitor").toLowerCase(),
    headline,
    meta,
    summary: distinctSummary(headline, item.summary),
    whyItMatters: limitSentences(whySource, WHY_MAX),
    suggestedAction: resolveSuggestedAction(item.suggested_action, meta.actionBucket, ACTION_MAX),
    sourceUrl: firstUrl(item),
  };
}

export function normalizeRegion(value: string): string {
  const raw = (value || "").trim();
  if (!raw) return "Global";
  const lower = raw.toLowerCase();
  if (lower.startsWith("united states") || lower.startsWith("u.s.") || lower === "us") {
    return "United States";
  }
  if (lower.includes("macau")) return "Macau";
  if (lower.startsWith("asia") || lower.includes("apac")) return "APAC";
  if (lower.startsWith("europe")) return "Europe";
  if (lower.startsWith("canada")) return "Canada";
  if (lower.startsWith("australia")) return "Australia";
  if (lower.startsWith("india")) return "India";
  if (lower.startsWith("israel")) return "Israel";
  if (lower.startsWith("philippines")) return "Philippines";
  if (raw.includes(" - ")) return raw.split(" - ")[0].trim();
  if (raw.includes(",")) return raw.split(",")[0].trim();
  return raw;
}

function groupByRegion(items: BriefingItem[]): RegionGroup[] {
  const groups = new Map<string, BriefingItem[]>();
  for (const item of items) {
    const region = normalizeRegion(item.meta.region);
    const bucket = groups.get(region);
    if (bucket) bucket.push(item);
    else groups.set(region, [item]);
  }
  return Array.from(groups.entries()).map(([region, regionItems]) => ({
    region,
    items: regionItems,
  }));
}

const ACTIONABLE_SIGNAL_TYPES = new Set([
  "sales_opportunity",
  "competitive_threat",
  "regulatory_development",
  "manufacturing_component_risk",
  "ai_product_signal",
  "technology_adoption_signal",
]);

function isActionItem(meta: StoryMeta, suggestedAction?: string | null): boolean {
  if (
    meta.actionBucket === "Monitor" ||
    meta.actionBucket === "Discuss with team" ||
    meta.actionBucket === "Immediate attention" ||
    meta.urgency === "Discuss" ||
    meta.urgency === "Immediate"
  ) {
    return true;
  }
  if (meta.signalType && ACTIONABLE_SIGNAL_TYPES.has(meta.signalType)) return true;
  if (meta.salesOpportunitySignal || meta.isCompetitorSignal) return true;
  if (isActionableSuggestion(suggestedAction)) return true;
  return false;
}

function sectionId(title: string): string {
  return title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

function computeKpis(items: BriefingItem[], topCount: number, actionCount: number): KpiMetric[] {
  let tech = 0;
  let competitor = 0;
  let regulatory = 0;
  for (const { meta } of items) {
    if (
      meta.signalType === "ai_product_signal" ||
      meta.signalType === "technology_adoption_signal" ||
      meta.category === "AI/ML" ||
      meta.category === "Computer Vision" ||
      meta.category === "Smart Tables" ||
      meta.category === "Semiconductors" ||
      meta.category === "Automation" ||
      meta.category === "Casino Tech"
    ) {
      tech += 1;
    }
    if (
      meta.signalType === "competitive_threat" ||
      meta.isCompetitorSignal ||
      meta.category === "Competitor" ||
      meta.category === "Supplier"
    ) {
      competitor += 1;
    }
    if (meta.category === "Regulation" || meta.category === "Compliance") regulatory += 1;
  }
  return [
    { key: "top", label: "Top Stories", value: topCount || Math.min(items.length, TOP_STORIES_LIMIT) },
    { key: "tech", label: "Tech Signals", value: tech },
    { key: "competitor", label: "Competitor Signals", value: competitor },
    { key: "regulatory", label: "Regulatory Alerts", value: regulatory },
    { key: "action", label: "Action Items", value: actionCount },
  ];
}

export function buildBriefing(digest: Digest): Briefing {
  const items = [...(digest.items ?? [])]
    .sort((a, b) => a.rank - b.rank)
    .map(toBriefingItem);

  const sections: BriefingSection[] = [];
  const assigned = new Set<string>();

  const topItems = items
    .filter((item) => {
      const metadata = asRecord(item.raw.metadata);
      return metadata.top_five_eligible === true;
    })
    .sort((a, b) => {
      const aMeta = asRecord(a.raw.metadata);
      const bMeta = asRecord(b.raw.metadata);
      const aRank = typeof aMeta.strategic_rank === "number" ? aMeta.strategic_rank : a.rank;
      const bRank = typeof bMeta.strategic_rank === "number" ? bMeta.strategic_rank : b.rank;
      return aRank - bRank;
    })
    .slice(0, TOP_STORIES_LIMIT);
  const resolvedTopItems = topItems;
  resolvedTopItems.forEach((item) => assigned.add(item.raw.id));
  if (resolvedTopItems.length) {
    sections.push({
      id: sectionId(SECTION.TOP_STORIES),
      title: SECTION.TOP_STORIES,
      featured: true,
      isActionList: false,
      items: resolvedTopItems,
      regions: null,
      count: resolvedTopItems.length,
    });
  }

  for (const title of CONTENT_SECTION_ORDER) {
    const sectionItems = items
      .filter((item) => !assigned.has(item.raw.id) && item.meta.section === title)
      .slice(0, CONTENT_SECTION_LIMIT);
    if (sectionItems.length) {
      sectionItems.forEach((item) => assigned.add(item.raw.id));
      sections.push({
        id: sectionId(title),
        title,
        featured: false,
        isActionList: false,
        items: sectionItems,
        regions: title === SECTION.COMPETITORS ? groupByRegion(sectionItems) : null,
        count: sectionItems.length,
      });
    } else if (ALWAYS_SHOW.has(title)) {
      sections.push({
        id: sectionId(title),
        title,
        featured: false,
        isActionList: false,
        items: [],
        regions: null,
        count: 0,
      });
    }
  }

  const actionItems = items
    .filter((item) => isActionItem(item.meta, item.raw.suggested_action))
    .slice(0, ACTION_ITEMS_LIMIT);
  if (actionItems.length) {
    sections.push({
      id: sectionId(SECTION.ACTION_ITEMS),
      title: SECTION.ACTION_ITEMS,
      featured: false,
      isActionList: true,
      items: actionItems,
      regions: null,
      count: actionItems.length,
    });
  }

  return {
    dateLabel: formatDateLong(digest.digest_date),
    windowLabel: `${formatDateTime(digest.window_start)} → ${formatDateTime(digest.window_end)}`,
    generatedLabel: formatDateTime(new Date().toISOString()),
    totalItems: items.length,
    sections,
    kpis: computeKpis(items, resolvedTopItems.length, actionItems.length),
  };
}

function formatDateLong(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
