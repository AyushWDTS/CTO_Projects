# Executive Command Center (Today Page)

## Overview

The Executive Command Center transforms the Today page from a simple agenda list into a comprehensive executive dashboard that answers critical questions and provides a timeline-based view of the day with contextual insights.

## Design Philosophy

### Executive Questions Answered

1. **What is happening today?** - Timeline with all events
2. **What is next?** - Next meeting highlighted in sidebar
3. **What requires preparation?** - Smart detection and counter
4. **Do I have travel today?** - Travel status card and sidebar
5. **How much free time remains?** - Calculated remaining free time

### Key Principles

1. **Timeline over List** - Chronological flow with free time blocks
2. **Visual Status** - Color-coded blocks (past, current, upcoming, free)
3. **Contextual Sidebar** - Executive insights and AI placeholders
4. **Dense Information** - No wasted whitespace
5. **Read-Only** - Pure information display, no interactions
6. **WDTS Design** - Consistent portal styling

## Architecture

### Components

#### Main Panel
**File:** `components/executive/executive-today-panel.tsx`

Orchestrates the command center:
- Fetches calendar, sync, and travel data
- Calculates statistics using `calculateTodayStats()`
- Builds timeline using `buildTodayTimeline()`
- Two-column layout (timeline + sidebar)
- Refresh functionality

#### Summary Cards
**File:** `components/executive/today-summary-cards.tsx`

Five key executive metrics:

1. **Meetings Today** (blue, Calendar icon) - Total count
2. **Next Meeting** (purple, Clock icon) - Time and title
3. **Free Time Left** (green, Coffee icon) - Hours/minutes remaining
4. **Travel Today** (amber/gray, Plane icon) - Yes/No
5. **Needs Prep** (red, AlertCircle icon) - Count of meetings requiring preparation

Each card:
- Colored icon
- Metric label
- Large value (2xl bold)
- Optional subtitle (for next meeting)

#### Timeline
**File:** `components/executive/today-timeline.tsx`

Chronological timeline with blocks for:
- **Meetings** - Blue blocks with details
- **Free Time** - Green blocks showing available time
- **Current** - Pulse animation + "Now" badge
- **Past** - Grayed out
- **Preparation** - Amber indicator for external/board meetings

**Visual Features:**
- Timeline indicator dots
- Color-coded borders and backgrounds
- Duration display
- Time range
- Location (with Teams/Zoom icons)
- Responsive card layout

#### Executive Sidebar
**File:** `components/executive/today-executive-sidebar.tsx`

Contextual information sections:

**Active Cards:**
1. **Next Meeting** - Shows upcoming meeting details
2. **Preparation Needed** - Count + checklist for prep work
3. **Travel Today** - Today's trip details if applicable
4. **Sync Status** - Freshness + last sync time

**AI Placeholders:**
5. **Meeting Brief** - AI-generated summaries (coming soon)
6. **Action Items** - Today's actions (coming soon)
7. **Key Decisions** - Decision tracking (coming soon)
8. **Weather** - Forecast (coming soon)
9. **Timezone** - Multi-timezone support (coming soon)

### Utilities

#### Today Utils
**File:** `lib/executive/today-utils.ts`

Core business logic:

**Statistics:**
- `calculateTodayStats()` - Compute all 5 metrics
  - Meetings count
  - Next meeting detection
  - Free time calculation (EOD minus remaining meetings)
  - Travel today detection
  - Preparation needs detection (external + board meetings)

**Timeline Building:**
- `buildTodayTimeline()` - Create timeline blocks
  - Convert calendar items to meeting blocks
  - Insert free time blocks (15+ minutes)
  - Mark past, current, next states
  - Sort chronologically
  - Handle 8 AM - 5 PM timeframe

**Utilities:**
- `formatDuration()` - Human-readable durations (e.g., "1h 30m")
- `calculateDurationMinutes()` - Minutes between dates

**Types:**
- `TodayStats` - Statistics shape
- `TimelineBlock` - Timeline item shape

## Data Flow

```
API Responses → Deduplication → Statistics → Timeline → Rendering
     ↓                                           ↓
  Sync/Travel (parallel)                    Sidebar Cards
```

1. **Fetch:** `/calendar/today`, `/sync/status`, `/travel/upcoming`
2. **Deduplicate:** Remove duplicate calendar items
3. **Stats:** Calculate 5 executive metrics
4. **Timeline:** Build chronological blocks with free time
5. **Render:** Timeline + Sidebar in two columns

## Timeline Block States

### Visual Indicators

**Past:**
- Gray border (`border-gray-200`)
- Gray background (`bg-gray-50`)
- Gray indicator dot (`bg-gray-300`)
- Gray text

**Current:**
- Green border (`border-green-300`)
- Green background (`bg-green-50`)
- Pulsing green dot (`bg-green-500 animate-pulse`)
- "Now" badge
- Green text

**Upcoming:**
- Blue border for meetings (`border-blue-200`)
- Blue background (`bg-blue-50/50`)
- Blue indicator dot (`bg-blue-500`)
- Amber dot if requires prep (`bg-amber-500`)

**Free Time:**
- Green border (`border-green-200`)
- Light green background (`bg-green-50/50`)
- Green indicator dot (`bg-green-400`)
- CheckCircle icon

## Statistics Calculation

### Meetings Today
Simple count of all calendar items (after deduplication).

### Next Meeting
- Filter future meetings
- Sort by start time
- Take first item
- Extract title, time, location

### Free Time Remaining
```
End of Day (5 PM) - Current Time - Σ(Remaining Meeting Durations)
```

- Calculate minutes until 5 PM
- Subtract all upcoming meeting durations
- Display in hours/minutes format

### Travel Today
- Check if any trip starts today
- Date comparison (today 00:00 to tomorrow 00:00)
- Boolean yes/no

### Pending Preparation
Count meetings that are:
- External (organizer not @wdtablesystems.com or @walkerdigital.com)
- OR contain "board" or "executive" in title

## Features

### Implemented ✓

- [x] 5 executive summary cards
- [x] Chronological timeline view
- [x] Free time blocks (15+ minutes)
- [x] Past/current/upcoming visual states
- [x] Pulse animation for current event
- [x] Preparation detection
- [x] Executive sidebar (9 sections)
- [x] Next meeting display
- [x] Travel today status
- [x] Sync status display
- [x] AI placeholder sections
- [x] Two-column layout
- [x] Sticky sidebar on desktop
- [x] Refresh functionality
- [x] WDTS design language
- [x] Responsive mobile layout

### Future Enhancements

- [ ] AI-generated meeting briefs
- [ ] Automated action item extraction
- [ ] Decision tracking
- [ ] Weather integration
- [ ] Multi-timezone display
- [ ] Document links
- [ ] Meeting recordings
- [ ] Smart scheduling suggestions
- [ ] Conflict warnings
- [ ] Travel time buffers

## Free Time Calculation Logic

1. **Start:** Current time
2. **End:** 5:00 PM (EOD)
3. **Meetings:** All future meetings today
4. **Formula:**
   ```
   Free Minutes = (EOD - Now) - Σ(Meeting Durations)
   Free Minutes = MAX(0, calculated) // Never negative
   ```

5. **Display:**
   - Under 60m: "45m"
   - Over 60m: "2h 30m"

## Preparation Detection

A meeting requires preparation if:

1. **External:** Organizer email NOT @wdtablesystems.com or @walkerdigital.com
2. **Board:** Title contains "board" or "executive"

**Display:**
- Count badge in summary card
- Amber dot on timeline block
- Sidebar card with checklist

**Checklist:**
- Review meeting materials
- Prepare discussion points
- Check attendee list

## Timeline Time Blocks

### Free Time Blocks

Only shown if **15+ minutes**:
- Less than 15m = too short, not displayed
- Prevents timeline clutter

**Visual:**
- Green styling
- "Free Time" title
- CheckCircle icon
- Duration display

### Meeting Blocks

**Information Shown:**
- Title (bold)
- Time range (e.g., "2:00 PM – 3:30 PM")
- Duration (e.g., "1h 30m")
- Location (with icon)
- Type badge (if applicable)
- Preparation indicator (amber circle)

## Responsive Behavior

### Desktop (lg+)
- Two-column grid: `lg:grid-cols-[1fr,380px]`
- Sidebar sticky: `lg:sticky lg:top-6`
- Full timeline width
- All cards visible

### Mobile
- Single column stack
- Sidebar below timeline
- Compact card display
- Touch-friendly targets

## Performance

- Parallel data fetching (3 APIs)
- Deduplication before processing
- Statistics calculated once
- Timeline built once per data change
- Minimal re-renders
- Efficient date comparisons

## Accessibility

- Semantic HTML structure
- ARIA labels on buttons
- Keyboard navigation
- Focus management
- Color contrast meets WCAG AA
- Screen reader friendly
- Status indicators

## Testing Checklist

- [ ] Empty day (no events)
- [ ] Single meeting
- [ ] Full day (8+ meetings)
- [ ] Free time blocks shown correctly
- [ ] Current event highlighted with pulse
- [ ] Past events grayed out
- [ ] Next meeting correct
- [ ] Free time calculation accurate
- [ ] Travel today detection works
- [ ] Preparation needs correct
- [ ] External meeting detection
- [ ] Board meeting detection
- [ ] Sidebar cards all visible
- [ ] Sync status displays
- [ ] Refresh functionality
- [ ] Responsive layout
- [ ] Timeline indicators correct
- [ ] Duration formatting correct

## Troubleshooting

**Issue:** Free time shows negative
- Check EOD time (5 PM)
- Verify MAX(0, ...) logic
- Confirm meeting duration calculations

**Issue:** Current event not highlighted
- Check date/time comparison
- Verify "Now" state logic
- Confirm pulse animation classes

**Issue:** Preparation needs wrong
- Check email domain detection
- Verify title substring matching
- Confirm organizer field exists

**Issue:** Timeline blocks wrong order
- Check sort by startTime
- Verify date parsing
- Confirm timezone handling

**Issue:** Sidebar not sticky
- Check `lg:sticky lg:top-6` classes
- Verify parent doesn't have `overflow`
- Confirm lg breakpoint

## Related Files

- `lib/executive/types.ts` - Type definitions
- `lib/executive/format.ts` - Formatting utilities
- `lib/executive-config.ts` - API query builders
- `components/state-blocks.tsx` - Loading/Error states

## Comparison: Before vs After

### Before
- Simple agenda list
- 3 basic stat cards
- No timeline visualization
- No free time indication
- No contextual insights
- Lots of whitespace
- Basic information only

### After
- Chronological timeline
- 5 rich executive metrics
- Visual timeline with free time blocks
- Current event pulse animation
- 9 sidebar insight cards
- Dense, useful information
- Next meeting always visible
- Preparation detection
- Travel status integration
- AI placeholder sections
- Two-column executive layout
- Command center feel

The Executive Command Center transforms the Today page into a comprehensive, timeline-based executive dashboard that answers all critical questions at a glance.
