"use client";

import { Clock, MapPin, Video, CheckCircle2, AlertCircle } from "lucide-react";
import { formatTimeOnly } from "@/lib/executive/format";
import { calculateDurationMinutes, formatDuration, type TimelineBlock } from "@/lib/executive/today-utils";

type TodayTimelineProps = {
  blocks: TimelineBlock[];
};

export function TodayTimeline({ blocks }: TodayTimelineProps) {
  if (blocks.length === 0) {
    return (
      <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-8 text-center">
        <Clock className="mx-auto h-12 w-12 text-[var(--muted)]" />
        <p className="mt-3 text-sm font-medium text-[var(--ink)]">No events scheduled</p>
        <p className="mt-1 text-xs text-[var(--muted)]">Your day is completely free</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-[var(--ink)]">Today&apos;s Timeline</h3>
      
      <div className="mt-4 space-y-2">
        {blocks.map((block) => (
          <TimelineBlockCard block={block} key={block.id} />
        ))}
      </div>
    </div>
  );
}

type TimelineBlockCardProps = {
  block: TimelineBlock;
};

function TimelineBlockCard({ block }: TimelineBlockCardProps) {
  const duration = calculateDurationMinutes(block.startTime, block.endTime);
  const timeRange = `${formatTimeOnly(block.startTime.toISOString())} – ${formatTimeOnly(block.endTime.toISOString())}`;
  
  // Determine styling based on block type and state
  const getBlockStyle = () => {
    if (block.isPast) {
      return {
        border: "border-gray-200",
        bg: "bg-gray-50",
        indicator: "bg-gray-300",
        text: "text-gray-500",
      };
    }
    
    if (block.isCurrent) {
      return {
        border: "border-green-300",
        bg: "bg-green-50",
        indicator: "bg-green-500 animate-pulse",
        text: "text-green-700",
      };
    }
    
    if (block.type === "free") {
      return {
        border: "border-green-200",
        bg: "bg-green-50/50",
        indicator: "bg-green-400",
        text: "text-green-700",
      };
    }
    
    if (block.type === "meeting") {
      return {
        border: "border-blue-200",
        bg: "bg-blue-50/50",
        indicator: block.requiresPrep ? "bg-amber-500" : "bg-blue-500",
        text: "text-blue-700",
      };
    }
    
    return {
      border: "border-[var(--line)]",
      bg: "bg-[var(--bg)]",
      indicator: "bg-[var(--primary)]",
      text: "text-[var(--ink)]",
    };
  };
  
  const style = getBlockStyle();
  
  return (
    <div className={`relative flex gap-3 rounded-lg border ${style.border} ${style.bg} p-3 transition`}>
      {/* Timeline indicator */}
      <div className="flex flex-col items-center">
        <div className={`h-3 w-3 rounded-full ${style.indicator}`} />
        {!block.isPast ? (
          <div className="mt-1 h-full w-0.5 bg-[var(--line)]" />
        ) : null}
      </div>
      
      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className={`font-semibold ${style.text} truncate`}>
                {block.title}
              </h4>
              {block.isCurrent ? (
                <span className="flex-shrink-0 rounded-full bg-green-600 px-2 py-0.5 text-xs font-semibold text-white">
                  Now
                </span>
              ) : null}
              {block.requiresPrep ? (
                <AlertCircle className="h-4 w-4 flex-shrink-0 text-amber-600" />
              ) : null}
            </div>
            
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-[var(--muted)]">
              <span className="inline-flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {timeRange}
              </span>
              <span>·</span>
              <span>{formatDuration(duration)}</span>
              
              {block.location ? (
                <>
                  <span>·</span>
                  <span className="inline-flex items-center gap-1 truncate">
                    {block.location.toLowerCase().includes("teams") ||
                    block.location.toLowerCase().includes("zoom") ? (
                      <Video className="h-3 w-3" />
                    ) : (
                      <MapPin className="h-3 w-3" />
                    )}
                    <span className="truncate">{block.location}</span>
                  </span>
                </>
              ) : null}
            </div>
          </div>
          
          {/* Type badge */}
          {block.type === "free" ? (
            <CheckCircle2 className="h-5 w-5 flex-shrink-0 text-green-600" />
          ) : null}
        </div>
      </div>
    </div>
  );
}
