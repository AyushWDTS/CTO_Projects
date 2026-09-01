"use client";

import { X, Video, MapPin, User, Calendar, ExternalLink, Users, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { formatExecutiveWhen } from "@/lib/executive/format";
import { executiveApi } from "@/lib/executive-api";
import type { ExecutiveMeeting, ExecutiveMeetingAttendee } from "@/lib/executive/types";

type MeetingDetailDrawerProps = {
  meeting: ExecutiveMeeting | null;
  onClose: () => void;
};

type MeetingDetailResponse = ExecutiveMeeting & {
  attendees?: ExecutiveMeetingAttendee[];
};

function getResponseStatusColor(status?: string): string {
  switch (status?.toLowerCase()) {
    case "accepted":
      return "text-green-600";
    case "declined":
      return "text-red-600";
    case "tentativelyaccepted":
    case "tentative":
      return "text-amber-600";
    default:
      return "text-[var(--muted)]";
  }
}

function formatResponseStatus(status?: string): string {
  switch (status?.toLowerCase()) {
    case "accepted":
      return "Accepted";
    case "declined":
      return "Declined";
    case "tentativelyaccepted":
    case "tentative":
      return "Tentative";
    case "none":
    case "notresponded":
      return "No response";
    default:
      return status || "Unknown";
  }
}

function formatRole(role?: string): string {
  switch (role?.toLowerCase()) {
    case "required":
      return "Required";
    case "optional":
      return "Optional";
    case "resource":
      return "Resource";
    default:
      return "";
  }
}

export function MeetingDetailDrawer({ meeting, onClose }: MeetingDetailDrawerProps) {
  const [fullMeeting, setFullMeeting] = useState<MeetingDetailResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!meeting) {
      setFullMeeting(null);
      return;
    }

    // If meeting already has attendees, use it directly
    if (meeting.attendees && meeting.attendees.length > 0) {
      setFullMeeting(meeting);
      return;
    }

    // Otherwise fetch full details
    setLoading(true);
    setError(null);
    executiveApi
      .fetchJson<MeetingDetailResponse>(`/meetings/${meeting.id}`)
      .then((data) => {
        setFullMeeting(data);
        setError(null);
      })
      .catch((err) => {
        console.error("Failed to fetch meeting details:", err);
        setError("Failed to load attendee information");
        setFullMeeting(meeting); // Fallback to basic info
      })
      .finally(() => {
        setLoading(false);
      });
  }, [meeting?.id]); // Only depend on meeting ID, not the whole object

  if (!meeting) return null;

  const displayMeeting = fullMeeting || meeting;
  const attendees = displayMeeting.attendees || [];

  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end bg-black/20 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div className="h-full w-full max-w-2xl overflow-y-auto bg-[var(--bg)] shadow-2xl">
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-[var(--line)] bg-[var(--surface)] px-6 py-4">
          <h2 className="text-lg font-semibold text-[var(--ink)]">Meeting Details</h2>
          <button
            className="rounded-lg p-2 text-[var(--muted)] transition hover:bg-[var(--bg)] hover:text-[var(--ink)]"
            onClick={onClose}
            type="button"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="space-y-6 p-6">
          {/* Title */}
          <section>
            <h3 className="text-2xl font-bold text-[var(--ink)]">
              {displayMeeting.title || "Meeting"}
            </h3>
          </section>

          {/* Date and Time */}
          <section className="flex items-start gap-3">
            <Calendar className="mt-0.5 h-5 w-5 flex-shrink-0 text-[var(--muted)]" />
            <div>
              <p className="text-sm font-medium text-[var(--ink)]">
                {formatExecutiveWhen(displayMeeting.start)}
                {displayMeeting.end ? ` – ${formatExecutiveWhen(displayMeeting.end)}` : ""}
              </p>
            </div>
          </section>

          {/* Organizer */}
          {displayMeeting.organizer ? (
            <section className="flex items-start gap-3">
              <User className="mt-0.5 h-5 w-5 flex-shrink-0 text-[var(--muted)]" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                  Organizer
                </p>
                <p className="mt-1 text-sm text-[var(--ink)]">{displayMeeting.organizer}</p>
              </div>
            </section>
          ) : null}

          {/* Attendees */}
          <section className="flex items-start gap-3">
            <Users className="mt-0.5 h-5 w-5 flex-shrink-0 text-[var(--muted)]" />
            <div className="flex-1">
              <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                Attendees
              </p>
              {loading ? (
                <div className="mt-3 flex items-center gap-2 text-sm text-[var(--muted)]">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Loading attendees...
                </div>
              ) : error ? (
                <p className="mt-2 text-sm text-amber-700">{error}</p>
              ) : attendees.length === 0 ? (
                <p className="mt-2 text-sm text-[var(--muted)]">No attendee information available</p>
              ) : (
                <ul className="mt-3 space-y-2">
                  {attendees.map((attendee, index) => (
                    <li className="rounded-lg border border-[var(--line)] bg-[var(--surface)] px-3 py-2" key={index}>
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-[var(--ink)] truncate">
                            {attendee.display_name || attendee.email}
                          </p>
                          {attendee.display_name ? (
                            <p className="mt-0.5 text-xs text-[var(--muted)] truncate">
                              {attendee.email}
                            </p>
                          ) : null}
                        </div>
                        <div className="flex flex-col items-end gap-1 flex-shrink-0">
                          <span
                            className={`text-xs font-medium ${getResponseStatusColor(attendee.response_status)}`}
                          >
                            {formatResponseStatus(attendee.response_status)}
                          </span>
                          {attendee.role ? (
                            <span className="text-xs text-[var(--muted)]">
                              {formatRole(attendee.role)}
                            </span>
                          ) : null}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          {/* Location */}
          {displayMeeting.location ? (
            <section className="flex items-start gap-3">
              <MapPin className="mt-0.5 h-5 w-5 flex-shrink-0 text-[var(--muted)]" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                  Location
                </p>
                <p className="mt-1 text-sm text-[var(--ink)]">{displayMeeting.location}</p>
              </div>
            </section>
          ) : null}

          {/* Teams Link */}
          {displayMeeting.join_url ? (
            <section className="flex items-start gap-3">
              <Video className="mt-0.5 h-5 w-5 flex-shrink-0 text-[var(--muted)]" />
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                  Online Meeting
                </p>
                <a
                  className="mt-1 inline-flex items-center gap-1 text-sm text-[var(--primary)] hover:underline"
                  href={displayMeeting.join_url}
                  rel="noopener noreferrer"
                  target="_blank"
                >
                  Join Microsoft Teams Meeting
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            </section>
          ) : null}
        </div>
      </div>
    </div>
  );
}
