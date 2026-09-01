# Executive Calendar - Monthly View

## Overview

The Executive Calendar tab has been redesigned from a simple today/week list view into a polished monthly calendar similar to Microsoft Teams or Outlook Calendar. It provides a comprehensive view of meetings, travel, flights, reminders, and other executive events across an entire month.

## Features

### Monthly Calendar Grid

- **Full month view**: 7-column grid showing all days of the selected month
- **Previous/next month navigation**: Navigate between months using arrow buttons
- **Today button**: Quick jump to current date and month
- **Visual indicators**:
  - Today's date highlighted with primary color badge
  - Selected date highlighted with ring border
  - Current month dates vs. adjacent month dates (faded)
  - Event count overflow indicator ("+X more")
- **Real-time data**: Fetches live calendar events from the Executive API

### Event Display

Events appear as compact colored chips inside date cells, showing:
- Event time (e.g., "2:00 PM")
- Event title (truncated if needed)
- Type-specific color coding (inferred from event title):
  - **Blue**: Meetings
  - **Purple**: Travel
  - **Indigo**: Flights
  - **Amber**: Reminders
  - **Red**: Board Reviews
  - **Green**: Vendor Calls
  - **Teal**: Internal Sync

Up to 3 events are shown per date cell. If more events exist, a "+X more" indicator is displayed.

### Day Detail Panel

Clicking any date opens a detailed side panel showing:
- Full date label (e.g., "Monday, August 31, 2026")
- Event count
- Events grouped by category:
  - **Meetings**: Standard meetings and calls
  - **Travel & Flights**: Travel segments and flight bookings
  - **Internal & Vendor**: Team syncs and vendor meetings
  - **Reminders & Reviews**: Board reviews and reminders

Each event card displays:
- Event title
- Start and end time
- Duration
- Location (with video icon for online meetings)
- Type badge with color coding

**Empty state**: When a selected date has no events, a clean empty state is shown with a calendar icon and helpful message.

## API Integration

The calendar fetches real-time data from the Executive API using a range-based endpoint.

**Endpoint**: `GET /executive/api/calendar/events`

**Query Parameters**:
- `startDate`: ISO date in `YYYY-MM-DD` format (e.g., "2026-08-01")
- `endDate`: ISO date in `YYYY-MM-DD` format (e.g., "2026-08-31")
- `timezone`: User's timezone (e.g., "Asia/Kolkata") - automatically included

**Response Format**: `ExecutiveCalendarRangeResponse`
```typescript
{
  start: string;
  end: string;
  range_start: string;
  range_end: string;
  timezone: string;
  as_of: string;
  events: ExecutiveCalendarEvent[];
  trips: ExecutiveTravelTrip[];
}
```

**Data Transformation**:
The component uses `transformCalendarResponse()` to convert the API response:
- **Meeting events** (`events` array) - Regular calendar items from Microsoft Graph/Gmail
- **Travel events** (`trips` array) - Travel and flight bookings
- Infers event type from title keywords (flight, travel, board, vendor, internal, reminder)
- Handles optional fields gracefully (title, location, dates)
- Filters out trips with missing start/end dates

**Loading States**:
- Shows loading spinner while fetching data
- Calendar grid displays events or empty states
- Month navigation triggers new date range queries

## Technical Implementation

### Components

1. **`ExecutiveCalendarPanel`** (`components/executive/executive-calendar-panel.tsx`)
   - Main container component
   - Manages current month and selected date state
   - Coordinates navigation and detail panel display

2. **`MonthNavigator`** (`components/executive/month-navigator.tsx`)
   - Month/year display
   - Previous/next month buttons
   - Today button

3. **`CalendarGrid`** (`components/executive/calendar-grid.tsx`)
   - 7-column calendar grid
   - Weekday headers
   - Date cells with event chips
   - Click handling for date selection

4. **`DayDetailPanel`** (`components/executive/day-detail-panel.tsx`)
   - Right-side detail panel
   - Event grouping and categorization
   - Empty state handling
   - Close button

### Utilities

**`lib/executive/calendar-utils.ts`** provides:
- `getMonthDays()`: Generates array of dates for calendar grid (including adjacent month days)
- `isSameDay()`: Date comparison utility
- `isToday()`: Check if date is today
- `isSameMonth()`: Check if date is in reference month
- `formatMonthYear()`: Format date as "Month Year"
- `getEventsForDay()`: Filter events for specific date
- `getEventTypeColor()`: Type-to-color mapping
- `getEventTypeLabel()`: Type-to-label mapping
- `transformCalendarResponse()`: Transform API response to CalendarEvent format
- `getMockCalendarEvents()`: Generate mock event data (for testing only)

### Type Definitions

```typescript
export type CalendarEvent = {
  id: string;
  title: string;
  start: Date;
  end: Date;
  type: "meeting" | "travel" | "flight" | "reminder" | "board" | "vendor" | "internal";
  location?: string;
  color?: string;
};
```

## Safe Defaults

The implementation follows defensive programming practices:
- `const allEvents = data ? transformCalendarResponse(data) : []` - safe array access
- Event filtering for trips with valid start/end times
- Handles optional fields (`title`, `location`, dates)
- Empty state rendering when `events.length === 0`
- Null checks for optional fields throughout
- Graceful handling of missing event data
- Loading states prevent UI crashes

## Styling

The calendar maintains consistency with the existing WDTS dashboard:
- Uses CSS custom properties (`--primary`, `--ink`, `--line`, `--surface`, etc.)
- Matches teal/red/white brand colors
- Follows established card and border styling patterns
- Responsive grid layout with `lg:grid-cols-[1fr,400px]`

## Future Enhancements

1. **Event Creation/Editing**
   - Add ability to create new events from empty date cells
   - Edit existing events from detail panel

2. **Filtering**
   - Filter by event type
   - Show/hide certain categories
   - Filter by provider (Microsoft, Gmail)

3. **Week/Day Views**
   - Add week view with hourly timeline
   - Add day view for detailed scheduling

4. **Search**
   - Search events by title, location, or attendees

5. **Multi-calendar Support**
   - Display events from multiple calendars
   - Color-code by calendar source

6. **Refresh Control**
   - Add manual refresh button
   - Auto-refresh on interval

7. **Recurring Event Details**
   - Show recurrence pattern in detail panel
   - Link to other instances

8. **Event Status**
   - Display tentative/confirmed status
   - Show declined/cancelled events differently

## User Experience

The calendar provides an executive-level view of upcoming commitments:
- **Information density**: See entire month at a glance
- **Quick navigation**: Jump between months or return to today instantly
- **Visual hierarchy**: Color-coded event types for rapid scanning
- **Detailed inspection**: Click any date for full schedule breakdown
- **Clean empty states**: No confusion when dates are free

The design balances information density with readability, making it ideal for busy executives who need to quickly assess their schedule and identify conflicts or gaps.
