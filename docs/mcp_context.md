# Using WDTS Executive Assistant from another project

Copy this file into the other repo (for example `docs/wdts-executive.md` or `.cursor/rules`). Do **not** copy the MCP source tree. Keep that platform in its own directory.

This project is a **client**. The Executive Assistant already runs as a local HTTP service.

## Prerequisite

On this machine, the MCP platform Docker stack must be up (from `Desktop/MCP/deploy`):

- Gateway: `http://localhost:8443`
- Health: `http://localhost:8443/health`

If health fails, start Compose in that deploy folder. Do not start a second copy of the stack from the UI repo.

## Auth

Use an API key with **`executive:read`** (created with `include_executive: true`).

```http
Authorization: Bearer wdts_live_...
```

Store the key only in the UI project’s env, for example `WDTS_EXECUTIVE_API_KEY`. Never commit it. Never call container ports `8300` / `8301` from the UI; only the gateway (`8443`) is public.

Your client IP must be allowed (`ALLOWED_CIDRS` on the gateway). Localhost is already allowed.

## For a UI: REST (recommended)

Base URL: `http://localhost:8443/executive/api`

| Need | Method | Path |
|------|--------|------|
| Sync freshness / errors | GET | `/sync/status` |
| Today’s agenda | GET | `/calendar/today?timezone=Asia/Kolkata` |
| Week agenda | GET | `/calendar/week?timezone=Asia/Kolkata` |
| Upcoming meetings | GET | `/meetings/upcoming?limit=20` |
| Past meetings | GET | `/meetings/past?limit=20` |
| Meeting details | GET | `/meetings/{meeting_id}` |
| Meeting brief | GET | `/meetings/{meeting_id}/brief` |
| Meeting summary | GET | `/meetings/{meeting_id}/summary` |
| Travel itinerary | GET | `/travel/upcoming` |
| One trip | GET | `/travel/{trip_id}` |
| Trip sources | GET | `/travel/{trip_id}/sources` |
| Action items | GET | `/action-items?status=open` |
| Decisions | GET | `/decisions?limit=20` |

Trigger sync (does not block; workers run in the background):

- `POST /sync/gmail` — body optional: `{"mode":"travel_backfill","days":90}`
- `POST /sync/graph` — Outlook mail + calendar

Example:

```ts
const base = process.env.WDTS_EXECUTIVE_BASE_URL ?? "http://localhost:8443/executive/api";
const key = process.env.WDTS_EXECUTIVE_API_KEY!;

async function executiveGet(path: string) {
  const res = await fetch(`${base}${path}`, {
    headers: { Authorization: `Bearer ${key}` },
  });
  if (!res.ok) throw new Error(`executive ${res.status}: ${await res.text()}`);
  return res.json();
}

const travel = await executiveGet("/travel/upcoming");
const agenda = await executiveGet("/calendar/today?timezone=Asia/Kolkata");
const sync = await executiveGet("/sync/status");
```

Treat empty lists as valid. Briefs may be `"source": "heuristic"`. Summaries can return `summary_not_found` until extract jobs have run. `sync.freshness` of `stale` usually means Gmail or Graph needs reconnect/sync, not a UI bug.

## For Cursor in the other workspace: MCP

`.cursor/mcp.json` in **that** project:

```json
{
  "mcpServers": {
    "wdts-executive": {
      "url": "http://localhost:8443/executive/mcp",
      "headers": {
        "Authorization": "Bearer <WDTS_EXECUTIVE_API_KEY>"
      }
    }
  }
}
```

MCP tools (same data as REST):

| Tool | Use |
|------|-----|
| `get_sync_status` | Freshness, providers, errors. `refresh=true` only enqueues sync. |
| `get_daily_agenda` | Day view. Pass `timezone` (e.g. `Asia/Kolkata`). |
| `get_upcoming_meetings` | Upcoming from the store. |
| `get_meeting_details` | One meeting by UUID. |
| `get_meeting_brief` | Prep checklist (heuristic if no LLM row). |
| `get_past_meeting_summary` | Post-meeting summary if stored. |
| `get_travel_itinerary` | Trips. Optional `trip_id` / `from_date`. |
| `list_action_items` | Default `status=open`. |
| `list_recent_decisions` | Recent decisions. |

Tools are **read-only** against the normalized database. They do not call Gmail/Graph inline. OAuth and workers live only in the MCP platform.

## Do not

- Copy `executive-assistant-mcp`, `gateway`, or `deploy/` into the UI repo.
- Embed Google/Microsoft OAuth in the UI.
- Mutate mail, calendar, or bookings (not supported).
- Point the UI at `localhost:8300` or `8301`.

## Connected accounts (this lab)

- Gmail: `ayushsaini2308@gmail.com` (travel mail)
- Microsoft: `aayush.saini@wdtablesystems.com` (calendar + Outlook travel)

If Gmail returns `invalid_grant`, reconnect via the MCP platform:

`GET http://localhost:8443/executive/api/oauth/gmail/start?email=ayushsaini2308@gmail.com`  
then open `auth_url` in a browser, then `POST /executive/api/sync/gmail`.


>>>>>>>>>>