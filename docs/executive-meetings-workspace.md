# Executive Meetings Workspace

## Overview

The Executive Meetings Workspace is a redesigned interface focused on executive usability, featuring a two-column layout, enhanced information hierarchy, and contextual insights.

## Design Philosophy

### Information Hierarchy

1. **Time as Primary Element** - Meeting time is the largest, most prominent text
2. **Two-Column Layout** - Main timeline + executive sidebar for context
3. **Reduced Whitespace** - Dense but scannable information layout
4. **Subtle Status Colors** - Visual cues without overwhelming design
5. **Grouped Filters** - Logical categorization (Time vs Type)

## Architecture

### Components

#### Main Panel
**File:** `components/executive/executive-meetings-panel.tsx`

Orchestrates the entire workspace:
- Fetches meeting data from `/meetings/upcoming`
- Manages week navigation state
- Handles filter state
- Coordinates two-column layout
- Shows meeting detail drawer on click

**Key Layout:**
```
├─ Header (title + refresh button)
├─ Summary Cards (5 metrics)
└─ Two-Column Grid
   ├─ Main Timeline (left, wider)
   │  ├─ Week Navigator
   │  ├─ Filters
   │  └─ Day Groups (meetings)
   └─ Executive Sidebar (right, 380px)
      ├─ Next Meeting
      ├─ Needs Preparation
      ├─ Upcoming Travel
      └─ Sync Status
```

#### Meeting Card (Enhanced)
**File:** `components/executive/meeting-card.tsx`

Redesigned with time as primary visual element:

**Visual Hierarchy:**
1. **Time** - 2xl bold (e.g., "2:30 PM")
2. **Duration** - Small with clock icon (e.g., "1h 30m")
3. **Title** - Semibold, truncated
4. **Organizer & Location** - Muted, truncated
5. **Badges** - Teams, External, Attendee count

**Features:**
- Status indicator bar (left border)
  - Blue: Upcoming
  - Green: In progress
  - Gray: Past
- Hover effects with animated chevron
- Automatic duration calculation
- Badge pills for context (Teams, External, Attendees)

#### Summary Cards (Enhanced)
**File:** `components/executive/meeting-summary-cards.tsx`

Five executive metrics with colored icons:

1. **This Week** - Total meetings (blue)
2. **Meeting Hours** - Time commitment (purple)
3. **Online** - Teams meetings (green)
4. **External** - External meetings (amber)
5. **Today** - Today's count (indigo)

Each card:
- Icon with semantic color
- Label in uppercase
- Large value (2xl bold)

#### Grouped Filters
**File:** `components/executive/meeting-filters.tsx`

Organized into two categories:

**Time Filters:**
- All, Today, This Week

**Type Filters:**
- Internal, External, Online

Each category has:
- Icon (Calendar for time, Filter for type)
- Label
- Pill-style buttons

#### Executive Sidebar
**File:** `components/executive/meetings-executive-sidebar.tsx`

Contextual information cards:

**1. Next Meeting**
- Icon: Clock (blue)
- Shows title, time, location
- Empty state: "No upcoming meetings"

**2. Needs Preparation**
- Icon: AlertCircle (amber)
- Shows meetings that are:
  - External, OR
  - Have 5+ attendees
- Limited to 3 items
- Displays title and time

**3. Upcoming Travel**
- Icon: Plane (green)
- Shows next 2 trips from `/travel/upcoming`
- Displays headline and start date

**4. Sync Status**
- Icon: Activity (purple)
- Shows freshness indicator
- Last successful sync timestamp

**Behavior:**
- Sticky on desktop (`lg:sticky lg:top-6`)
- Stacks below on mobile
- Fetches travel and sync data independently

#### Detail Drawer
**File:** `components/executive/meeting-detail-drawer.tsx`

(Unchanged from previous version)
- Slides in from right
- Shows full meeting details
- Attendees with response status
- Teams link
- Organizer, location, date/time

### Utilities

#### Format Utils
**File:** `lib/executive/format.ts`

Added `formatTimeOnly()` for time display:
```typescript
formatTimeOnly("2026-09-01T14:30:00Z") // "2:30 PM"
```

#### Meetings Utils
**File:** `lib/executive/meetings-utils.ts`

(Unchanged) Provides:
- Week range calculation
- Day grouping
- Filtering logic
- Next meeting finder

## Data Flow

```
API → State Management → Filtering → Grouping → Two-Column Render
                      ↓
                   Sidebar (parallel fetches)
```

1. **Fetch:** Main meetings from `/meetings/upcoming`
2. **Filter:** Apply time/type filters
3. **Group:** Organize by day
4. **Render:** Main timeline + sidebar
5. **Sidebar Data:** Parallel fetches for travel and sync

## Features

### Implemented ✓

- [x] Two-column layout (main + sidebar)
- [x] Time as primary visual element
- [x] Enhanced summary cards with icons
- [x] Grouped filters (Time/Type)
- [x] Status indicator bars
- [x] Subtle status colors
- [x] Meeting badges (Teams, External, Attendees)
- [x] Executive sidebar with context
- [x] Needs preparation detection
- [x] Travel integration
- [x] Sync status display
- [x] Sticky sidebar on desktop
- [x] Responsive mobile layout

### Future Enhancements

- [ ] Meeting intelligence (agenda extraction)
- [ ] Pre-meeting briefings
- [ ] Post-meeting summaries
- [ ] Action items tracking
- [ ] Conflict detection
- [ ] Travel time warnings
- [ ] Preparation reminders
- [ ] Meeting analytics
- [ ] Calendar optimization suggestions

## UI/UX Principles

1. **Scannable** - Large time makes schedule scanning instant
2. **Contextual** - Sidebar provides relevant insights
3. **Organized** - Grouped filters prevent confusion
4. **Dense** - More information in less space
5. **Executive** - No technical jargon, business-focused

## Styling

Uses WDTS portal variables + semantic colors:

**Status Colors:**
- Blue (#3B82F6): Upcoming meetings, "This Week" metric
- Green (#10B981): In-progress meetings, "Online" metric
- Amber (#F59E0B): Needs prep, "External" metric
- Purple (#8B5CF6): Meeting hours metric
- Indigo (#6366F1): Today metric
- Gray (#6B7280): Past meetings

**Badge Colors:**
- Blue-100: Teams badge
- Amber-100: External badge
- Gray-100: Attendee count badge

## Responsive Behavior

### Desktop (lg+)
- Two-column grid: `lg:grid-cols-[1fr,380px]`
- Sidebar sticky: `lg:sticky lg:top-6`
- Full filter labels visible

### Tablet/Mobile
- Single column stack
- Sidebar appears below timeline
- Filters wrap gracefully
- Touch-friendly tap targets

## Performance

- Parallel data fetching (meetings, travel, sync)
- Calculated metrics memoized
- No expensive re-renders
- Lazy drawer mounting

## Accessibility

- Semantic HTML structure
- ARIA labels on buttons
- Keyboard navigation
- Focus management in drawer
- Color contrast meets WCAG AA
- Screen reader friendly

## Testing Checklist

- [ ] Empty state (no meetings)
- [ ] Single meeting
- [ ] Full week of meetings
- [ ] Filter by time (all, today, this week)
- [ ] Filter by type (internal, external, online)
- [ ] Week navigation (prev, next, today)
- [ ] Meeting card click → drawer opens
- [ ] Next meeting shows correctly
- [ ] Needs preparation detection works
- [ ] Travel integration displays
- [ ] Sync status shows
- [ ] Status colors correct (upcoming, in-progress, past)
- [ ] Duration calculation accurate
- [ ] Badges display (Teams, External, Attendees)
- [ ] Responsive layout on mobile
- [ ] Sidebar sticky on desktop

## Troubleshooting

**Issue:** Sidebar not sticking
- Check `lg:sticky lg:top-6 lg:self-start` classes
- Verify parent doesn't have `overflow` property

**Issue:** Wrong status colors
- Check `getStatusColor()` logic in `meeting-card.tsx`
- Verify meeting start/end times are valid

**Issue:** Duration not showing
- Ensure both start and end times exist
- Check `calculateDuration()` function

**Issue:** Needs preparation empty
- Verify organizer email format
- Check attendee count threshold (currently 5+)

**Issue:** Travel not showing
- Confirm `/travel/upcoming` API is accessible
- Check `useExecutiveQuery` in sidebar component

## Related Files

- `lib/executive/types.ts` - Type definitions
- `lib/executive/format.ts` - Formatting utilities
- `lib/executive/meetings-utils.ts` - Business logic
- `components/executive/week-navigator.tsx` - Week controls
- `components/executive/meeting-detail-drawer.tsx` - Detail view
- `components/state-blocks.tsx` - Loading/Error states

## Comparison: Before vs After

### Before
- Single-column layout
- Title as primary element
- Simple 3-card summary
- Flat filter list
- Lots of whitespace
- No contextual information

### After
- Two-column layout
- Time as primary element
- 5 rich metric cards
- Grouped filters (Time/Type)
- Dense information layout
- Executive sidebar with context
- Status indicator bars
- Smart badges
- Needs preparation detection
- Travel integration
- Enhanced visual hierarchy
