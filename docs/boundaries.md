# Boundaries

CTO monorepo rules for product isolation and shared code.

## Products

| Product | Location | Owns |
|---------|----------|------|
| Briefing | `apps/briefing-api`, `apps/briefing-web` | News pipeline, digests, bookmarks, `news_intelligence` DB |
| Executive UI | `apps/briefing-web` (`/cto` tabs + BFF), optional `apps/executive-web` dev sandbox | Calendar / meetings / travel UX; data via Executive REST only |

## Allowed shares

- `@wdts/ui` — presentational UI primitives
- `@wdts/api-client` — generic HTTP helpers with configurable base URL

## Forbidden

- Microsoft Graph SDK or Graph credentials in Briefing (or anywhere under `apps/briefing-*`)
- Shared database between news and executive data
- Executive domain logic inside `apps/briefing-api`
- Exposing `WDTS_EXECUTIVE_API_KEY` (or any executive secret) via `NEXT_PUBLIC_*`
- Building an `ms-collab-api` / Graph backend in this monorepo
- OAuth reconnect, sync POST, or mutation controls in v1 Executive UI

## Executive BFF (briefing-web)

- Browser calls same-origin `/executive/api/...` only (REST, not `/executive/mcp`)
- Server env: `WDTS_EXECUTIVE_BASE_URL` + `WDTS_EXECUTIVE_API_KEY` (server-only)
- Upstream: `{WDTS_EXECUTIVE_BASE_URL}/executive/api/<rest>` — no doubled `/executive`
- **GET only** with v1 allowlist: sync/status, calendar/today|week|events, meetings/* (upcoming + detail), travel/*
- `/travel/upcoming` is curated in the BFF (heuristic filter + optional Bedrock) before the `/cto` Travel tab
- `/meetings/upcoming` is normalized in the BFF (field name mapping: `subject` → `title`, `starts_at` → `start`, `organizer_email` → `organizer`)
- `/calendar/events` provides range-based calendar access for the Calendar tab's monthly grid
- Denied until approved: oauth/*, admin/*, sync/gmail, sync/graph, action-items, decisions

See [mcp_context.md](mcp_context.md) for gateway ops and API reference.
See [meetings-workspace.md](meetings-workspace.md) for Meetings tab feature documentation.
See [calendar-monthly-view.md](calendar-monthly-view.md) for Calendar tab feature documentation.

## Workspaces

- npm workspaces: `apps/*` + `packages/js/*`
- `apps/briefing-api` is Python-only — do not treat it as a Node app
