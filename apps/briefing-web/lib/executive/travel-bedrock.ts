import {
  BedrockRuntimeClient,
  ConverseCommand,
  type ConverseCommandOutput,
} from "@aws-sdk/client-bedrock-runtime";
import { fromIni } from "@aws-sdk/credential-providers";

import type { ExecutiveTravelTrip } from "@/lib/executive/types";
import {
  formatSegmentDetail,
  formatSegmentLabel,
  heuristicTripHeadline,
  heuristicTripSummary,
  isPlausibleTravelTrip,
  plausibleSegments,
} from "@/lib/executive/travel-heuristic";
import type { ExecutiveCuratedTravelTrip } from "@/lib/executive/types";

type BedrockTravelRow = {
  id: string;
  include: boolean;
  headline?: string;
  summary?: string;
};

type BedrockTravelResponse = {
  trips: BedrockTravelRow[];
};

function bedrockConfigured(): boolean {
  const modelId = (process.env.BEDROCK_MODEL_ID ?? process.env.WDTS_EXECUTIVE_BEDROCK_MODEL_ID ?? "").trim();
  return Boolean(modelId);
}

function createBedrockClient(): BedrockRuntimeClient {
  const region = (process.env.AWS_REGION ?? "ap-south-1").trim();
  const profile = (process.env.AWS_PROFILE ?? "").trim();
  return new BedrockRuntimeClient({
    region,
    credentials: profile ? fromIni({ profile }) : undefined,
  });
}

function extractBedrockText(response: ConverseCommandOutput): string {
  const parts = response.output?.message?.content ?? [];
  const text = parts
    .map((part) => ("text" in part && part.text ? part.text : ""))
    .join("")
    .trim();
  if (!text) throw new Error("empty_bedrock_response");
  return text;
}

function parseBedrockJson(text: string): BedrockTravelResponse {
  const trimmed = text.trim();
  const jsonText = trimmed.startsWith("{")
    ? trimmed
    : trimmed.slice(trimmed.indexOf("{"), trimmed.lastIndexOf("}") + 1);
  const parsed = JSON.parse(jsonText) as BedrockTravelResponse;
  if (!Array.isArray(parsed.trips)) throw new Error("invalid_bedrock_travel_shape");
  return parsed;
}

function compactTripInput(trip: ExecutiveTravelTrip) {
  return {
    id: trip.id,
    title: trip.title ?? null,
    starts_at: trip.starts_at ?? null,
    ends_at: trip.ends_at ?? null,
    segments: plausibleSegments(trip).map((segment) => ({
      type: segment.segment_type ?? null,
      origin: segment.origin ?? null,
      destination: segment.destination ?? null,
      confirmation_code: segment.confirmation_code ?? null,
      starts_at: segment.starts_at ?? null,
    })),
  };
}

function fallbackCuratedTrip(trip: ExecutiveTravelTrip): ExecutiveCuratedTravelTrip {
  const segments = plausibleSegments(trip);
  return {
    id: trip.id,
    headline: heuristicTripHeadline(trip),
    summary: heuristicTripSummary(trip),
    starts_at: trip.starts_at ?? segments[0]?.starts_at ?? null,
    ends_at: trip.ends_at ?? segments[segments.length - 1]?.ends_at ?? null,
    itinerary: segments.slice(0, 6).map((segment) => ({
      label: formatSegmentLabel(segment),
      detail: formatSegmentDetail(segment),
    })),
  };
}

export async function curateTravelWithBedrock(
  trips: ExecutiveTravelTrip[],
): Promise<{ trips: ExecutiveCuratedTravelTrip[]; method: "bedrock" | "heuristic" }> {
  const candidates = trips.filter(isPlausibleTravelTrip);
  if (candidates.length === 0) {
    return { trips: [], method: "heuristic" };
  }

  if (!bedrockConfigured()) {
    return {
      trips: candidates.map(fallbackCuratedTrip),
      method: "heuristic",
    };
  }

  const modelId = (process.env.BEDROCK_MODEL_ID ?? process.env.WDTS_EXECUTIVE_BEDROCK_MODEL_ID ?? "").trim();
  const client = createBedrockClient();
  const prompt = [
    "You curate executive travel for a CTO dashboard.",
    "Given extracted trip candidates from email/calendar heuristics, return JSON only:",
    '{"trips":[{"id":"...","include":true,"headline":"...","summary":"..."}]}',
    "Rules:",
    "- include=false for certification reminders, Jira updates, job postings, or non-travel mail.",
    "- include=true only for real flights, hotels, trains, or ground transport.",
    "- headline: short executive title (destination or route).",
    "- summary: one sentence with dates/routes if known.",
    "Input trips:",
    JSON.stringify(candidates.map(compactTripInput)),
  ].join("\n");

  try {
    const response = await client.send(
      new ConverseCommand({
        modelId,
        system: [{ text: "Return valid JSON only. No markdown fences." }],
        messages: [{ role: "user", content: [{ text: prompt }] }],
        inferenceConfig: { temperature: 0.1, maxTokens: 2048 },
      }),
    );

    const parsed = parseBedrockJson(extractBedrockText(response));
    const byId = new Map(parsed.trips.map((row) => [row.id, row]));
    const curated: ExecutiveCuratedTravelTrip[] = [];

    for (const trip of candidates) {
      const row = byId.get(trip.id);
      if (row && row.include === false) continue;

      const base = fallbackCuratedTrip(trip);
      curated.push({
        ...base,
        headline: row?.headline?.trim() || base.headline,
        summary: row?.summary?.trim() || base.summary,
      });
    }

    return { trips: curated, method: "bedrock" };
  } catch {
    return {
      trips: candidates.map(fallbackCuratedTrip),
      method: "heuristic",
    };
  }
}
