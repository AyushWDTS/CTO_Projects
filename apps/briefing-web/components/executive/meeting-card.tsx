"use client";

import { Video, Clock, Users, MapPin, ChevronRight } from "lucide-react";
import { formatExecutiveWhen, formatTimeOnly } from "@/lib/executive/format";
import type { ExecutiveMeeting } from "@/lib/executive/types";

type MeetingCardProps = {
  meeting: ExecutiveMeeting;
  onClick: () => void;
};

export function MeetingCard({ meeting, onClick }: MeetingCardProps) {
  const hasTeamsLink = Boolean(meeting.join_url);
  const isInternal = (meeting.organizer ?? "").toLowerCase().includes("@wdtablesystems.com") || 
                     (meeting.organizer ?? "").toLowerCase().includes("@walkerdigital.com");
  
  const startTime = meeting.start ? formatTimeOnly(meeting.start) : "";
  const endTime = meeting.end ? formatTimeOnly(meeting.end) : "";
  const duration = calculateDuration(meeting.start ?? null, meeting.end ?? null);

  return (
    <button
      className="group relative w-full overflow-hidden rounded-xl border border-[var(--line)] bg-[var(--surface)] p-4 text-left transition hover:border-[var(--primary)] hover:shadow-md"
      onClick={onClick}
      type="button"
    >
      {/* Status indicator bar */}
      <div className={`absolute left-0 top-0 h-full w-1 ${getStatusColor(meeting)}`} />
      
      <div className="ml-2 flex gap-4">
        {/* Time column (primary visual) */}
        <div className="flex-shrink-0 w-20">
          <div className="text-2xl font-bold text-[var(--ink)]">
            {startTime}
          </div>
          {duration ? (
            <div className="mt-1 flex items-center gap-1 text-xs text-[var(--muted)]">
              <Clock className="h-3 w-3" />
              <span>{duration}</span>
            </div>
          ) : null}
        </div>

        {/* Meeting details */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <h4 className="font-semibold text-[var(--ink)] truncate">
                {meeting.title ?? "Untitled meeting"}
              </h4>
              
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
                {meeting.organizer ? (
                  <span className="truncate max-w-[200px]">{meeting.organizer}</span>
                ) : null}
                
                {meeting.organizer && meeting.location ? (
                  <span>·</span>
                ) : null}
                
                {meeting.location ? (
                  <span className="flex items-center gap-1 truncate max-w-[150px]">
                    <MapPin className="h-3 w-3 flex-shrink-0" />
                    {meeting.location}
                  </span>
                ) : null}
              </div>

              {/* Badges */}
              <div className="mt-2 flex flex-wrap items-center gap-2">
                {hasTeamsLink ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
                    <Video className="h-3 w-3" />
                    Teams
                  </span>
                ) : null}
                
                {!isInternal ? (
                  <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                    External
                  </span>
                ) : null}
                
                {meeting.attendees && meeting.attendees.length > 0 ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">
                    <Users className="h-3 w-3" />
                    {meeting.attendees.length}
                  </span>
                ) : null}
              </div>
            </div>

            {/* Arrow indicator */}
            <ChevronRight className="h-5 w-5 flex-shrink-0 text-[var(--muted)] transition group-hover:translate-x-1 group-hover:text-[var(--primary)]" />
          </div>
        </div>
      </div>
    </button>
  );
}

function getStatusColor(meeting: ExecutiveMeeting): string {
  const now = new Date();
  const start = meeting.start ? new Date(meeting.start) : null;
  const end = meeting.end ? new Date(meeting.end) : null;

  if (start && end) {
    if (now >= start && now <= end) {
      return "bg-green-500"; // In progress
    }
    if (now > end) {
      return "bg-gray-300"; // Past
    }
  }
  
  return "bg-blue-500"; // Upcoming
}

function calculateDuration(start: string | null, end: string | null): string {
  if (!start || !end) return "";
  
  const startDate = new Date(start);
  const endDate = new Date(end);
  const diffMinutes = Math.round((endDate.getTime() - startDate.getTime()) / (1000 * 60));
  
  if (diffMinutes < 60) {
    return `${diffMinutes}m`;
  }
  
  const hours = Math.floor(diffMinutes / 60);
  const minutes = diffMinutes % 60;
  
  return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
}
