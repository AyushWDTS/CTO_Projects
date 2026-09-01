# Calendar Monthly View - Backend Requirements

## Current State

The Calendar tab has been fully implemented with a polished monthly grid UI, but is currently using a **fallback approach** due to missing backend support.

## What's Working

- Monthly calendar grid with navigation
- Event display as colored chips in date cells
- Day detail panel with categorized events
- Event type inference and color coding
- Loading and error states
- Mock data fallback for demonstration

## What's Missing: Backend Endpoint

The Executive API currently provides:
- `GET /executive/api/calendar/today` - Today's events
- `GET /executive/api/calendar/week` - This week's events

**Not available:**
- `GET /executive/api/calendar/month` - Full month of events

## Current Fallback Behavior

The Calendar component currently:
1. Calls `GET /executive/api/calendar/week?timezone=Asia/Kolkata`
2. Transforms any returned events
3. **Falls back to mock data** if API returns no events
4. Displays a visible amber banner: "Demo Mode: Displaying sample events"

This ensures the UI is fully functional and demonstrates all features while waiting for backend implementation.

## Required Backend Implementation

### Recommended: Range-Based Calendar Endpoint

**Route**: `GET /executive/api/calendar/events`

**Query Parameters**:
- `startDate` (required): ISO date in `YYYY-MM-DD` format (e.g., "2026-08-01")
- `endDate` (required): ISO date in `YYYY-MM-DD` format (e.g., "2026-08-31")
- `timezone` (optional): IANA timezone (e.g., "Asia/Kolkata") - defaults to user's configured timezone

**Why Range-Based?**
- More flexible than month/week/day-specific endpoints
- Supports arbitrary date ranges for various UI needs
- Single endpoint for all calendar views (month, week, day, custom ranges)
- Easier to implement pagination and caching
- Follows REST best practices for resource filtering

**Response Format**: Stable shape with consistent structure
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Product Review",
      "start": "2026-08-05T14:00:00+05:30",
      "end": "2026-08-05T15:30:00+05:30",
      "location": "Conference Room A",
      "organizer": "john@example.com",
      "provider": "microsoft",
      "type": "meeting"
    },
    {
      "id": "uuid",
      "title": "Flight to Macau",
      "start": "2026-08-10T15:00:00+05:30",
      "end": "2026-08-10T20:00:00+05:30",
      "location": "Delhi Airport",
      "provider": "gmail",
      "type": "flight"
    }
  ],
  "startDate": "2026-08-01",
  "endDate": "2026-08-31",
  "source": "graph",
  "timezone": "Asia/Kolkata"
}
```

**Response Fields**:
- `items` (array, required): Array of calendar events (empty array if none exist)
- `startDate` (string, required): Echoes the requested start date
- `endDate` (string, required): Echoes the requested end date
- `source` (string, required): Data source - one of `"graph"`, `"gmail"`, `"internal"`, or `"mock"`
- `timezone` (string, required): Timezone used for date calculations

**Event Item Fields**:
- `id` (string, required): Unique event identifier
- `title` (string, required): Event title/subject
- `start` (string, required): ISO 8601 datetime with timezone
- `end` (string, required): ISO 8601 datetime with timezone
- `location` (string, optional): Event location or meeting URL
- `organizer` (string, optional): Organizer email address
- `provider` (string, required): Source provider - `"microsoft"`, `"gmail"`, or `"internal"`
- `type` (string, optional): Event type hint - `"meeting"`, `"travel"`, `"flight"`, `"reminder"`, `"board"`, `"vendor"`, `"internal"`

**Data Requirements**:
- Return all calendar events within the specified date range (inclusive)
- Include events from all connected providers (Gmail, Microsoft Graph)
- Support standard field names: `title`, `start`, `end`, `location`, `organizer`
- Also support legacy field names for backward compatibility: `subject`, `starts_at`, `ends_at`, `organizer_email`
- Return empty `items` array when no events exist (not an error condition)
- Handle multi-day events correctly (events that span multiple dates)
- Return events in chronological order by start time

### Implementation Notes

The backend should:
1. Query the normalized calendar database for events in the specified date range
2. Parse `startDate` and `endDate` as local dates in the user's timezone
3. Include events that overlap the range (start OR end within range)
4. Filter by the user's connected calendar providers
5. Return events in chronological order by start time
6. Handle timezone conversion consistently
7. Support event types: meetings, travel, flights, reminders, board reviews, vendor calls, internal syncs
8. Return stable response shape even when `items` is empty

### Edge Cases to Handle

1. **Empty Range**: Return `{"items": [], "startDate": "...", "endDate": "...", "source": "...", "timezone": "..."}`
2. **Invalid Date Range**: Return 400 error if `endDate` is before `startDate`
3. **Multi-Day Events**: Include events that start before `startDate` but end within range
4. **Timezone Boundaries**: Use the specified timezone for date boundary calculations
5. **No Connected Providers**: Return empty items array with `source: "mock"` or appropriate message

### Frontend Integration

Once the `/calendar/events` endpoint is available:

1. **Update the BFF allowlist** (`lib/executive-bff-allowlist.ts`):
   ```typescript
   const ALLOWED_PATTERNS: RegExp[] = [
     // ... existing patterns
     /^calendar\/events$/,  // Add this pattern
   ];
   ```

2. **Create a range-based query helper** (`lib/executive-config.ts`):
   ```typescript
   export function executiveCalendarRangeQuery(
     startDate: Date,
     endDate: Date
   ): Record<string, string> {
     return {
       startDate: startDate.toISOString().split('T')[0],
       endDate: endDate.toISOString().split('T')[0],
       timezone: getExecutiveTimezone(),
     };
   }
   ```

3. **Update Calendar component** (`components/executive/executive-calendar-panel.tsx`):
   ```typescript
   export function ExecutiveCalendarPanel() {
     const [currentMonth, setCurrentMonth] = useState<Date>(new Date());
     
     // Calculate first and last day of the displayed month
     const firstDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
     const lastDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0);
     
     // Fetch events for the entire month using range endpoint
     const rangeParams = executiveCalendarRangeQuery(firstDay, lastDay);
     const { data, error, loading } = useExecutiveQuery<ExecutiveCalendarRangeResponse>(
       "/calendar/events",
       rangeParams
     );
     
     // Remove mock data fallback - use real API data
     const apiItems = data?.items ?? [];
     const allEvents = transformCalendarItems(apiItems);
     
     // ... rest of component
   }
   ```

4. **Define response type** (`lib/executive/types.ts`):
   ```typescript
   export type ExecutiveCalendarRangeResponse = {
     items: ExecutiveCalendarItem[];
     startDate: string;
     endDate: string;
     source: "graph" | "gmail" | "internal" | "mock";
     timezone: string;
   };
   ```

5. **Remove the demo mode fallback logic**:
   - Remove `getMockCalendarEvents()` call
   - Remove `usingMockData` variable
   - Remove the amber demo mode banner from JSX
   - The calendar will work with real data or show empty states naturally

## Testing Checklist

Once backend is implemented:

**Backend Tests:**
- [ ] Endpoint returns events for specified date range
- [ ] Endpoint validates `startDate` and `endDate` format
- [ ] Endpoint returns 400 if `endDate` is before `startDate`
- [ ] Timezone parameter is respected for date boundary calculations
- [ ] Events from all providers (Gmail, Microsoft Graph) are included
- [ ] Multi-day events that overlap the range are included
- [ ] Both new (`title`, `start`) and legacy (`subject`, `starts_at`) field names work
- [ ] Empty date ranges return valid response with empty `items` array
- [ ] Response shape is stable (always includes all required fields)
- [ ] Events are returned in chronological order

**Frontend Integration Tests:**
- [ ] BFF allowlist includes `/calendar/events` pattern
- [ ] Calendar component calculates correct month start/end dates
- [ ] Calendar fetches events for the displayed month
- [ ] Frontend displays all events in calendar grid
- [ ] Month navigation triggers new date range queries
- [ ] Multi-day events display correctly
- [ ] Empty months show appropriate empty states
- [ ] Demo mode banner is removed
- [ ] No console errors or 404s
- [ ] Loading states display during fetch
- [ ] Error states display on API failures

## Example API Calls

### Fetch events for August 2026
```bash
GET /executive/api/calendar/events?startDate=2026-08-01&endDate=2026-08-31&timezone=Asia/Kolkata
```

**Response:**
```json
{
  "items": [
    {
      "id": "abc-123",
      "title": "Leadership Sync",
      "start": "2026-08-02T09:00:00+05:30",
      "end": "2026-08-02T10:00:00+05:30",
      "location": null,
      "organizer": "ceo@example.com",
      "provider": "microsoft",
      "type": "internal"
    }
  ],
  "startDate": "2026-08-01",
  "endDate": "2026-08-31",
  "source": "graph",
  "timezone": "Asia/Kolkata"
}
```

### Empty range (no events)
```bash
GET /executive/api/calendar/events?startDate=2027-01-01&endDate=2027-01-31&timezone=Asia/Kolkata
```

**Response:**
```json
{
  "items": [],
  "startDate": "2027-01-01",
  "endDate": "2027-01-31",
  "source": "graph",
  "timezone": "Asia/Kolkata"
}
```

## Priority

**High** - The Calendar tab is fully built and ready, just waiting for backend support. Once this range-based endpoint is implemented, the feature will be production-ready.

## Benefits of Range-Based Design

1. **Flexibility**: Single endpoint serves month view, week view, day view, and custom ranges
2. **Simplicity**: Frontend calculates the range, backend returns events in that range
3. **Caching**: Easier to implement intelligent caching strategies
4. **Testing**: Easier to test edge cases with arbitrary date ranges
5. **Future-Proof**: Supports new calendar views without new endpoints
6. **REST Compliance**: Follows resource filtering best practices

## Contact

For questions about the frontend implementation or data format requirements, refer to:
- `docs/calendar-monthly-view.md` - Full feature documentation
- `docs/boundaries.md` - API integration boundaries
- `lib/executive/calendar-utils.ts` - Data transformation logic
