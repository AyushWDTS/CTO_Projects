# Executive Meetings Workspace

Full-featured executive meeting workspace on the `/cto` dashboard Meetings tab.

## Features

### Week Navigation
- Navigate between weeks (Previous Week, This Week, Next Week)
- Current week indicator
- Week range display (e.g., "Aug 25 – Aug 31")

### Meeting Grouping
- Meetings grouped by day (Monday through Sunday)
- Today indicator badge
- Empty state for days with no meetings
- Sorted chronologically within each day

### Summary Cards
1. **Total meetings this week** — Count of meetings in the selected week
2. **Meetings today** — Count of meetings scheduled for today
3. **Next meeting** — Time and title of the next upcoming meeting

### Filters
- **All** — Show all meetings for the selected week
- **Today** — Show only today's meetings
- **This Week** — Show only this week's meetings
- **Internal** — Meetings with @wdtablesystems.com or @walkerdigital.com organizers
- **External** — Meetings with external organizers
- **Teams / Online** — Meetings with a Teams join link

### Meeting Cards
- Meeting title, time, organizer, location
- Visual indicator for online/Teams meetings (video icon)
- Click to open detail drawer

### Meeting Detail Drawer
Full meeting details in a slide-over panel:
- Title
- Date and time
- Organizer
- **Attendee list with RSVP status** (fetched from `/meetings/{id}`)
  - Display name and email
  - Response status (Accepted, Declined, Tentative, No response)
  - Role (Required, Optional, Resource)
  - Color-coded status indicators
- Location
- Teams link (when available)
- Description/body preview (when available)
- Source data (meeting ID, provider)
- Placeholders for future features (brief, preparation)

## Data Flow

```
MCP Gateway → BFF (/executive/api/meetings/upcoming) → Client (list view)
              ↓ normalization
          subject → title
          starts_at → start
          organizer_email → organizer

MCP Gateway → BFF (/executive/api/meetings/{id}) → Client (detail drawer)
              ↓ includes attendees array
          Attendees with email, display_name, role, response_status
```

## Components

| Component | Path | Purpose |
|-----------|------|---------|
| `ExecutiveMeetingsPanel` | `components/executive/executive-meetings-panel.tsx` | Main container |
| `WeekNavigator` | `components/executive/week-navigator.tsx` | Week selection controls |
| `MeetingSummaryCards` | `components/executive/meeting-summary-cards.tsx` | KPI summary cards |
| `MeetingFilters` | `components/executive/meeting-filters.tsx` | Filter controls |
| `MeetingCard` | `components/executive/meeting-card.tsx` | Individual meeting card |
| `MeetingDetailDrawer` | `components/executive/meeting-detail-drawer.tsx` | Meeting detail slide-over |
| `meetings-utils` | `lib/executive/meetings-utils.ts` | Week/day grouping, filtering logic |
| `meetings-normalize` | `lib/executive/meetings-normalize.ts` | BFF field name normalization |

## API Integration

### Endpoints
**List:** `GET /executive/api/meetings/upcoming?limit=100`
**Detail:** `GET /executive/api/meetings/{meeting_id}` (includes attendees)

### Normalization (BFF)
The BFF normalizes MCP response field names:
- `subject` → `title`
- `starts_at` → `start`
- `ends_at` → `end`
- `organizer_email` → `organizer`

### Client-side Processing
Since the API only supports "upcoming meetings" (not week-specific queries), the client:
1. Fetches up to 100 upcoming meetings
2. Filters meetings for the selected week range
3. Groups by day (Monday–Sunday)
4. Applies active filter (all, today, internal, etc.)

## Read-Only Constraints
All features are **read-only**. The following actions are **not available**:
- Edit meeting details
- RSVP or change attendance
- Send email to organizer/attendees
- Trigger sync or calendar mutation

## Future Enhancements
Planned features (UI placeholders exist):
- AI-generated meeting brief
- Preparation data (agenda, documents, action items)

## Testing
Visit `http://localhost:3000/cto` → **Meetings** tab.

Ensure the MCP gateway is running at `http://localhost:8443` and has synced calendar data.
