import { NextRequest, NextResponse } from "next/server";
import overviewFixture from "@/fixtures/overview.json";
import calendarFixture from "@/fixtures/calendar.json";
import meetingsFixture from "@/fixtures/meetings.json";
import travelFixture from "@/fixtures/travel.json";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = {
  params: { path?: string[] };
};

const FIXTURES: Record<string, unknown> = {
  "": overviewFixture,
  overview: overviewFixture,
  calendar: calendarFixture,
  meetings: meetingsFixture,
  travel: travelFixture,
};

function fixtureFor(pathSegments: string[]): unknown {
  const key = pathSegments[0] ?? "";
  return FIXTURES[key] ?? {
    source: "fixture",
    title: "Unavailable",
    message: `No fixture mapped for /executive/api/${pathSegments.join("/")}`,
    path: pathSegments,
  };
}

function fixtureResponse(pathSegments: string[], reason: string): NextResponse {
  const body = fixtureFor(pathSegments);
  return NextResponse.json(
    {
      ...(typeof body === "object" && body !== null ? body : { data: body }),
      _meta: { fixture: true, reason },
    },
    {
      status: 200,
      headers: {
        "x-executive-source": "fixture",
        "x-executive-fixture-reason": reason,
      },
    },
  );
}

function buildUpstreamUrl(baseUrl: string, pathSegments: string[], search: string): string {
  const base = baseUrl.replace(/\/$/, "");
  const rest = pathSegments.join("/");
  const path = rest ? `/executive/api/${rest}` : "/executive/api";
  return `${base}${path}${search}`;
}

async function proxy(request: NextRequest, context: RouteContext): Promise<NextResponse> {
  const pathSegments = context.params.path ?? [];
  const forceFixtures = process.env.EXECUTIVE_USE_FIXTURES === "true";
  const baseUrl = process.env.EXECUTIVE_MCP_BASE_URL?.trim();
  const apiKey = process.env.EXECUTIVE_API_KEY?.trim();

  if (forceFixtures || !baseUrl) {
    return fixtureResponse(
      pathSegments,
      forceFixtures ? "EXECUTIVE_USE_FIXTURES=true" : "EXECUTIVE_MCP_BASE_URL unset",
    );
  }

  const upstreamUrl = buildUpstreamUrl(baseUrl, pathSegments, request.nextUrl.search);
  const headers = new Headers();
  const accept = request.headers.get("accept");
  const contentType = request.headers.get("content-type");
  if (accept) headers.set("accept", accept);
  else headers.set("accept", "application/json");
  if (contentType) headers.set("content-type", contentType);
  if (apiKey) headers.set("Authorization", `Bearer ${apiKey}`);

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
  };

  if (request.method !== "GET" && request.method !== "HEAD") {
    init.body = await request.arrayBuffer();
  }

  try {
    const upstream = await fetch(upstreamUrl, init);
    if (upstream.status >= 500) {
      return fixtureResponse(pathSegments, `upstream_${upstream.status}`);
    }

    const responseHeaders = new Headers();
    const upstreamContentType = upstream.headers.get("content-type");
    if (upstreamContentType) responseHeaders.set("content-type", upstreamContentType);
    responseHeaders.set("x-executive-source", "upstream");

    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error: unknown) {
    const reason = error instanceof Error ? error.message : "upstream_unreachable";
    return fixtureResponse(pathSegments, reason);
  }
}

export async function GET(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function POST(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function PUT(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function PATCH(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}

export async function DELETE(request: NextRequest, context: RouteContext) {
  return proxy(request, context);
}
