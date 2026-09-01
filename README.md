# CTO Project

Modular monorepo for WDTS CTO apps.

- Product isolation: [docs/boundaries.md](docs/boundaries.md)
- Layout & BFF: [docs/architecture.md](docs/architecture.md)

## Structure

| Path | Role |
|------|------|
| `apps/briefing-api` | News intelligence FastAPI (Python) |
| `apps/briefing-web` | News dashboard / Daily Briefing (Next.js, port 3000) |
| `apps/executive-web` | Executive calendar/meetings/travel UI + BFF (Next.js, port 3001) |
| `packages/js/api-client` | `@wdts/api-client` |
| `packages/js/ui` | `@wdts/ui` |

## Prerequisites

- Node 20+ and npm 10+ (workspaces)
- Python 3.12+ and venv for `briefing-api`
- Postgres for Briefing (`news_intelligence`)

## Install JS workspaces

From the repo root:

```bash
npm install
```

This links `apps/briefing-web`, `apps/executive-web`, and `packages/js/*`.  
`apps/briefing-api` has no `package.json` and is not a Node app.

## Run Briefing API

```bash
cd apps/briefing-api
python3.13 -m venv .venv          # if missing / after path moves
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Note: moving the project invalidates an old venv’s absolute shebangs — recreate `.venv` if `uvicorn` fails to start.
## Run Briefing web

```bash
cd apps/briefing-web
npm run dev
# http://localhost:3000
```

Set `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` if needed.

### Executive data on `/cto`

Executive calendar/meetings/travel tabs on [`http://localhost:3000/cto`](http://localhost:3000/cto) use a read-only BFF at `/executive/api/*`.

Add to `apps/briefing-web/.env.local` (server-only — never `NEXT_PUBLIC_*` for the key):

- `WDTS_EXECUTIVE_BASE_URL=http://localhost:8443`
- `WDTS_EXECUTIVE_API_KEY=wdts_live_...`
- `WDTS_EXECUTIVE_TIMEZONE=Asia/Kolkata` (optional)

Prerequisite: Executive gateway health at `http://localhost:8443/health`. See [docs/mcp_context.md](docs/mcp_context.md).

Smoke tests (with `npm run dev` running):

```bash
curl -s http://localhost:3000/executive/api/sync/status | head
curl -s "http://localhost:3000/executive/api/calendar/today?timezone=Asia/Kolkata" | head
curl -s http://localhost:3000/executive/api/meetings/upcoming?limit=5 | head
curl -s http://localhost:3000/executive/api/travel/upcoming | head
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:3000/executive/api/sync/gmail
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:3000/executive/api/sync/graph
```

Expect `403` for disallowed paths and `405` for POST.

## Run Executive web (optional dev sandbox)

```bash
cd apps/executive-web
cp .env.example .env.local   # optional; without BASE_URL, BFF serves fixtures
npm run dev
# http://localhost:3001
```

Server-only env for the sandbox (prefer `WDTS_EXECUTIVE_*` on briefing-web):

- `WDTS_EXECUTIVE_BASE_URL` / `WDTS_EXECUTIVE_API_KEY` on briefing-web `/cto`
