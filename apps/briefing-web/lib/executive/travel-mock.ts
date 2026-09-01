import type { ExecutiveTravelUpcomingCurated, ExecutiveCuratedTravelTrip } from "./types";

/**
 * Generate mock travel data for demo purposes.
 * Returns realistic executive travel itineraries.
 */
export function getMockTravelData(): ExecutiveTravelUpcomingCurated {
  const today = new Date();
  const nextWeek = new Date(today);
  nextWeek.setDate(today.getDate() + 7);
  
  const twoWeeks = new Date(today);
  twoWeeks.setDate(today.getDate() + 14);
  
  const threeWeeks = new Date(today);
  threeWeeks.setDate(today.getDate() + 21);

  const trips: ExecutiveCuratedTravelTrip[] = [
    {
      id: "mock-trip-1",
      headline: "Business Trip to Singapore",
      summary: "Quarterly board meeting and strategic partner discussions",
      starts_at: nextWeek.toISOString(),
      ends_at: new Date(nextWeek.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString(),
      itinerary: [
        {
          label: "Outbound Flight",
          detail: `${formatDateShort(nextWeek)} · Singapore Airlines SQ 401 · DEL → SIN · Business Class · Departs 09:45 AM IST · Arrives 05:15 PM SGT`,
        },
        {
          label: "Hotel",
          detail: "Marina Bay Sands · Deluxe Room · 3 nights · Confirmation #MB847392 · Check-in: 3:00 PM",
        },
        {
          label: "Ground Transport",
          detail: "Airport transfer arranged · Executive car service · Contact: +65 9XXX XXXX",
        },
        {
          label: "Return Flight",
          detail: `${formatDateShort(new Date(nextWeek.getTime() + 3 * 24 * 60 * 60 * 1000))} · Singapore Airlines SQ 406 · SIN → DEL · Business Class · Departs 11:30 PM SGT`,
        },
      ],
    },
    {
      id: "mock-trip-2",
      headline: "Trip to Macau for Gaming Conference",
      summary: "Annual Asia Gaming Summit attendance and networking",
      starts_at: twoWeeks.toISOString(),
      ends_at: new Date(twoWeeks.getTime() + 2 * 24 * 60 * 60 * 1000).toISOString(),
      itinerary: [
        {
          label: "Outbound Flight",
          detail: `${formatDateShort(twoWeeks)} · Air India AI 319 · DEL → HKG → MFM · Economy · Departs 02:15 PM IST`,
        },
        {
          label: "Hotel",
          detail: "The Venetian Macao · Resort Suite · 2 nights · Confirmation #VM293847",
        },
        {
          label: "Conference Registration",
          detail: "Asia Gaming Summit 2026 · Venetian Convention Center · Executive Pass · Badge #AGS-2026-E-0432",
        },
        {
          label: "Return Flight",
          detail: `${formatDateShort(new Date(twoWeeks.getTime() + 2 * 24 * 60 * 60 * 1000))} · Air India AI 320 · MFM → HKG → DEL · Departs 08:45 AM HKT`,
        },
      ],
    },
    {
      id: "mock-trip-3",
      headline: "Dubai Office Site Visit",
      summary: "New office location inspection, team meetings, and client presentations",
      starts_at: threeWeeks.toISOString(),
      ends_at: new Date(threeWeeks.getTime() + 4 * 24 * 60 * 60 * 1000).toISOString(),
      itinerary: [
        {
          label: "Outbound Flight",
          detail: `${formatDateShort(threeWeeks)} · Emirates EK 512 · DEL → DXB · Business Class · Departs 03:25 AM IST · Arrives 05:45 AM GST`,
        },
        {
          label: "Hotel",
          detail: "Address Downtown Dubai · Premier Room · 4 nights · Corporate booking · Confirmation #AD2026-4839",
        },
        {
          label: "Ground Transport",
          detail: "Dedicated car service · BMW 7 Series · Driver: Ahmed · Contact: +971 50 XXX XXXX",
        },
        {
          label: "Meeting Schedule",
          detail: "Day 1: Office tour & HR meetings · Day 2: Client presentations · Day 3: Team strategy session",
        },
        {
          label: "Return Flight",
          detail: `${formatDateShort(new Date(threeWeeks.getTime() + 4 * 24 * 60 * 60 * 1000))} · Emirates EK 513 · DXB → DEL · Business Class · Departs 09:50 PM GST`,
        },
      ],
    },
  ];

  return {
    as_of: today.toISOString(),
    trips,
  };
}

function formatDateShort(date: Date): string {
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
