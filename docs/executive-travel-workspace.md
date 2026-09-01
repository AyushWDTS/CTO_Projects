# Executive Travel Workspace

## Overview

The Executive Travel Workspace is a comprehensive dashboard for managing and viewing executive travel schedules. It transforms raw travel data into an intuitive, executive-friendly interface with rich metadata, filters, and detailed views.

## Architecture

### Components

#### Main Panel
**File:** `components/executive/executive-travel-panel.tsx`

The main orchestrator component that:
- Fetches travel data from `/travel/upcoming` API
- Handles mock data fallback for demo purposes
- Manages filter state and trip selection
- Coordinates all child components

#### Summary Cards
**File:** `components/executive/travel-summary-cards.tsx`

Displays high-level travel statistics:
- Upcoming Trips count
- Countries count
- Flights count
- Hotels count
- Next Departure (date + destination)

#### Travel Filters
**File:** `components/executive/travel-filters.tsx`

Provides filtering controls:
- Status filters: All, Upcoming, Completed
- Country filters (dynamic based on trips)
- Clean, pill-style UI

#### Trip Card
**File:** `components/executive/travel-trip-card.tsx`

Individual trip display with timeline appearance:
- Destination (hero text, largest)
- Purpose/reason for travel
- Date range and duration
- Status badge (Upcoming/In Progress/Completed)
- Transport icons (Flight/Hotel/Ground)
- Country badge
- Timeline indicator (left border)
- Hover effects and click interaction

#### Detail Drawer
**File:** `components/executive/travel-detail-drawer.tsx`

Expandable side panel for full trip details:
- Complete trip summary
- All itinerary items with icons
- Detail cards for dates, duration, country, status
- Placeholder section for future features

### Utilities

#### Workspace Utils
**File:** `lib/executive/travel-workspace-utils.ts`

Core business logic:

**Data Enrichment:**
- `extractDestination()` - Parse destination from headline
- `extractCountry()` - Map destination to country
- `extractPurpose()` - Get trip purpose from summary
- `calculateDuration()` - Calculate trip length in days
- `getTripStatus()` - Determine if upcoming/in-progress/completed
- `analyzeItinerary()` - Detect flights, hotels, ground transport

**Metadata:**
- `TripWithMetadata` type - Extended trip with computed fields
- `enrichTripWithMetadata()` - Add all metadata to a trip

**Aggregation:**
- `calculateTravelStats()` - Compute summary statistics
- `groupTripsByMonth()` - Organize trips chronologically by month

**Filtering:**
- `filterTrips()` - Apply status, country, purpose filters

#### Mock Data
**File:** `lib/executive/travel-mock.ts`

Demo data generator:
- 3 realistic travel scenarios
- Singapore (business), Macau (conference), Dubai (site visit)
- Detailed itineraries with flights, hotels, ground transport
- Automatic date generation (next week, 2 weeks, 3 weeks out)

## Data Flow

```
API Response → Mock Fallback → Enrichment → Filtering → Grouping → Display
```

1. **Fetch:** `useExecutiveQuery` fetches from `/travel/upcoming`
2. **Fallback:** If no real trips, use `getMockTravelData()`
3. **Enrich:** Each trip gets metadata via `enrichTripWithMetadata()`
4. **Filter:** Apply user-selected filters
5. **Group:** Organize by month via `groupTripsByMonth()`
6. **Display:** Render in timeline UI with month headers

## Features

### Implemented ✓

- [x] Executive summary cards
- [x] Compact demo mode notification
- [x] Monthly chronological organization
- [x] Destination-first card design
- [x] Status badges
- [x] Transport/accommodation icons
- [x] Timeline appearance (left border indicator)
- [x] Expandable detail drawer
- [x] Filters (status, country)
- [x] WDTS styling consistency
- [x] Responsive layout

### Future Enhancements (Placeholder in Drawer)

- [ ] Weather forecast for destination
- [ ] Timezone converter
- [ ] Currency exchange rates
- [ ] Required travel documents
- [ ] Meeting schedule during trip
- [ ] Emergency contacts
- [ ] Calendar integration
- [ ] Expense tracking
- [ ] Travel policy compliance
- [ ] Carbon footprint

## UI/UX Principles

1. **Destination First:** Largest text, immediate recognition
2. **Executive Clarity:** No technical jargon, clear language
3. **Progressive Disclosure:** Summary cards → Trip cards → Detail drawer
4. **Visual Hierarchy:** Timeline indicator, status badges, icons
5. **Actionable:** Click to expand, filter to focus
6. **Responsive:** Works on desktop, tablet, mobile

## Styling

Uses WDTS portal variables:
- `--primary` - Brand color for accents
- `--ink` - Primary text
- `--muted` - Secondary text
- `--surface` - Card backgrounds
- `--bg` - Page background
- `--line` - Borders

## Mock Data vs Real Data

**Mock Data Conditions:**
- API returns empty `trips` array
- Still shows demo notification
- Automatically replaced when real data syncs

**Real Data:**
- Comes from Gmail/Microsoft calendar parsing
- Curated via Bedrock or heuristics
- No demo notification shown

## Testing Checklist

- [ ] Empty state (no trips)
- [ ] Mock data state (demo mode)
- [ ] Real data state (production)
- [ ] Filter by status (all, upcoming, completed)
- [ ] Filter by country
- [ ] Trip card click → drawer opens
- [ ] Drawer close button
- [ ] Drawer backdrop click closes
- [ ] Monthly grouping correct
- [ ] Next departure calculation
- [ ] Statistics accuracy
- [ ] Refresh button functionality
- [ ] Responsive layout on mobile/tablet

## Troubleshooting

**Issue:** Trips not showing
- Check API endpoint `/travel/upcoming` response
- Verify `trips` array structure matches `ExecutiveCuratedTravelTrip` type
- Check browser console for errors

**Issue:** Mock data always showing
- Verify API is returning `trips.length > 0`
- Check network tab for successful API response
- Confirm MCP platform is synced

**Issue:** Destination extraction wrong
- Update `extractDestination()` pattern matching in `travel-workspace-utils.ts`
- Add more patterns to handle different headline formats

**Issue:** Country not recognized
- Add country mapping to `extractCountry()` in `travel-workspace-utils.ts`

## Performance

- No expensive computations in render
- Filtering and grouping happen once per data change
- Drawer renders only when trip selected
- Lazy loading for future enhancements

## Accessibility

- Semantic HTML (buttons, sections, lists)
- ARIA labels where needed
- Keyboard navigation support
- Focus management in drawer
- Color contrast meets WCAG AA

## Related Files

- `lib/executive/types.ts` - Type definitions
- `lib/executive/format.ts` - Date formatting utilities
- `components/executive/executive-panel-shell.tsx` - Layout wrapper
- `components/state-blocks.tsx` - Loading/Error/Empty states
