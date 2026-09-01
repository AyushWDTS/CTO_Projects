import { NextRequest, NextResponse } from "next/server";
import { isExecutivePathAllowed } from "@/lib/executive-bff-allowlist";
import type { ExecutiveTravelUpcoming } from "@/lib/executive/types";
import { curateExecutiveTravel } from "@/lib/executive/travel-curate";
import { normalizeMeetingsResponse, normalizeSingleMeeting } from "@/lib/executive/meetings-normalize";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = {
  params: { path?: string[] };
};

function buildUpstreamUrl(baseUrl: string, pathSegments: string[], search: string): string {
  const base = baseUrl.replace(/\/$/, "");
  const rest = pathSegments.join("/");
  return `${base}/executive/api/${rest}${search}`;
}

function forbiddenResponse(pathSegments: string[]): NextResponse {
  return NextResponse.json(
    {
      detail: "Path not allowed on Executive BFF (v1 read-only allowlist).",
      path: pathSegments.join("/"),
    },
    { status: 403, headers: { "x-executive-source": "bff-deny" } },
  );
}

function misconfiguredResponse(): NextResponse {
  return NextResponse.json(
    {
      detail: "Executive BFF is not configured. Set WDTS_EXECUTIVE_BASE_URL and WDTS_EXECUTIVE_API_KEY.",
    },
    { status: 503, headers: { "x-executive-source": "bff-config" } },
  );
}

async function proxyGet(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const pathSegments = context.params.path ?? [];

  if (!isExecutivePathAllowed(pathSegments)) {
    return forbiddenResponse(pathSegments);
  }

  const baseUrl = process.env.WDTS_EXECUTIVE_BASE_URL?.trim();
  const apiKey = process.env.WDTS_EXECUTIVE_API_KEY?.trim();

  if (!baseUrl || !apiKey) {
    return misconfiguredResponse();
  }

  const upstreamUrl = buildUpstreamUrl(baseUrl, pathSegments, request.nextUrl.search);
  const headers = new Headers({ Accept: "application/json" });
  headers.set("Authorization", `Bearer ${apiKey}`);

  try {
    const upstream = await fetch(upstreamUrl, {
      method: "GET",
      headers,
      cache: "no-store",
    });

    const responseHeaders = new Headers();
    const upstreamContentType = upstream.headers.get("content-type");
    if (upstreamContentType) responseHeaders.set("content-type", upstreamContentType);
    responseHeaders.set("x-executive-source", "upstream");

    const isTravelUpcoming =
      pathSegments.length === 2 &&
      pathSegments[0] === "travel" &&
      pathSegments[1] === "upcoming";

    const isMeetingsUpcoming =
      pathSegments.length === 2 &&
      pathSegments[0] === "meetings" &&
      pathSegments[1] === "upcoming";

    const isMeetingDetail =
      pathSegments.length === 2 &&
      pathSegments[0] === "meetings" &&
      pathSegments[1] !== "upcoming" &&
      pathSegments[1] !== "past";

    if (isTravelUpcoming && upstream.ok) {
      const payload = (await upstream.json()) as ExecutiveTravelUpcoming;
      const curated = await curateExecutiveTravel(payload);
      responseHeaders.set("content-type", "application/json");
      responseHeaders.set("x-executive-source", "bff-travel-curate");
      return NextResponse.json(curated, { status: 200, headers: responseHeaders });
    }

    if (isMeetingsUpcoming && upstream.ok) {
      const payload = await upstream.json();
      const normalized = normalizeMeetingsResponse(payload);
      responseHeaders.set("content-type", "application/json");
      responseHeaders.set("x-executive-source", "bff-meetings-normalize");
      return NextResponse.json(normalized, { status: 200, headers: responseHeaders });
    }

    if (isMeetingDetail && upstream.ok) {
      const payload = await upstream.json();
      const normalized = normalizeSingleMeeting(payload);
      responseHeaders.set("content-type", "application/json");
      responseHeaders.set("x-executive-source", "bff-meeting-normalize");
      return NextResponse.json(normalized, { status: 200, headers: responseHeaders });
    }

    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "upstream_unreachable";
    return NextResponse.json(
      { detail: "Executive upstream unreachable.", error: message },
      { status: 502, headers: { "x-executive-source": "bff-error" } },
    );
  }
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxyGet(request, context);
}

export async function POST() {
  return NextResponse.json({ detail: "Method not allowed (v1 read-only BFF)." }, { status: 405 });
}

export async function PUT() {
  return NextResponse.json({ detail: "Method not allowed (v1 read-only BFF)." }, { status: 405 });
}

export async function PATCH() {
  return NextResponse.json({ detail: "Method not allowed (v1 read-only BFF)." }, { status: 405 });
}

export async function DELETE() {
  return NextResponse.json({ detail: "Method not allowed (v1 read-only BFF)." }, { status: 405 });
}
