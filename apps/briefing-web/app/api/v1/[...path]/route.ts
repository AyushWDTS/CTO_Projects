import { NextRequest, NextResponse } from "next/server";

/**
 * Proxy for briefing-api (Python FastAPI backend).
 * Forwards /api/v1/* requests to the Python service.
 */

const BRIEFING_API_BASE_URL = process.env.BRIEFING_API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function GET(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToBriefingApi(request, params.path, "GET");
}

export async function POST(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToBriefingApi(request, params.path, "POST");
}

export async function PUT(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToBriefingApi(request, params.path, "PUT");
}

export async function DELETE(request: NextRequest, { params }: { params: { path: string[] } }) {
  return proxyToBriefingApi(request, params.path, "DELETE");
}

async function proxyToBriefingApi(
  request: NextRequest,
  pathSegments: string[],
  method: string
): Promise<NextResponse> {
  const path = pathSegments.join("/");
  const searchParams = request.nextUrl.searchParams.toString();
  const url = `${BRIEFING_API_BASE_URL}/api/v1/${path}${searchParams ? `?${searchParams}` : ""}`;

  try {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    const options: RequestInit = {
      method,
      headers,
    };

    // Forward request body for POST/PUT
    if (method === "POST" || method === "PUT") {
      const body = await request.text();
      if (body) {
        options.body = body;
      }
    }

    const response = await fetch(url, options);
    const data = await response.text();

    return new NextResponse(data, {
      status: response.status,
      headers: {
        "Content-Type": response.headers.get("Content-Type") || "application/json",
      },
    });
  } catch (error) {
    console.error(`Proxy error for ${method} ${url}:`, error);
    return NextResponse.json(
      { error: "Failed to connect to briefing API", detail: String(error) },
      { status: 502 }
    );
  }
}
