# Architecture

CTO monorepo layout for WDTS apps.

## Apps vs packages

```text
apps/
  briefing-api/     Python FastAPI — news pipeline (Postgres news_intelligence)
  briefing-web/     Next.js — Daily Briefing + pipeline lab (:3000)
  executive-web/    Next.js — calendar / meetings / travel (:3001) + BFF

packages/js/
  api-client/       @wdts/api-client — configurable HTTP helpers
  ui/               @wdts/ui — shared presentational primitives
```

`apps/briefing-api` is Python-only. npm workspaces include `apps/*` + `packages/js/*`; do not run Node scripts against briefing-api.

## Data flow

```text
briefing-web  --->  briefing-api  --->  news_intelligence DB

executive-web (browser)
    |
    |  same-origin /executive/api/*
    v
executive-web BFF (Route Handlers)
    |  Authorization: Bearer EXECUTIVE_API_KEY
    |  {EXECUTIVE_MCP_BASE_URL}/executive/api/<rest>
    v
Executive MCP REST (dedicated VM)
```

No shared DB between Briefing and Executive. No Microsoft Graph code in Briefing.

## Executive BFF

Server-only env:

- `EXECUTIVE_MCP_BASE_URL` — upstream host (no trailing slash required)
- `EXECUTIVE_API_KEY` — injected as `Authorization: Bearer …`
- `EXECUTIVE_USE_FIXTURES=true` — force UI-contract fixtures

Never put the API key in `NEXT_PUBLIC_*`.

Upstream URL rule (no doubled `/executive`):

```text
Client:   /executive/api/calendar
Upstream: {BASE}/executive/api/calendar
```

If MCP is unset, forced to fixtures, unreachable, or returns 5xx, the BFF returns fixtures from `apps/executive-web/fixtures/` so shells still render.

See [boundaries.md](boundaries.md) for isolation rules.
