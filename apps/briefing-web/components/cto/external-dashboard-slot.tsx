"use client";

type ExternalDashboardSlotProps = {
  title: string;
  description: string;
  /** Optional iframe URL when another team’s dashboard is ready to embed. */
  embedUrl?: string | null;
  ownerLabel?: string;
};

export function ExternalDashboardSlot({
  title,
  description,
  embedUrl,
  ownerLabel = "another team",
}: ExternalDashboardSlotProps) {
  const url = embedUrl?.trim() || null;

  if (url) {
    return (
      <section className="space-y-3">
        <div>
          <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">{description}</p>
        </div>
        <div className="overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--surface)]">
          <iframe
            className="h-[min(78vh,900px)] w-full bg-white"
            src={url}
            title={title}
          />
        </div>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-dashed border-[var(--line)] bg-[var(--surface)] px-6 py-16 text-center">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--primary)]">
        Integration slot
      </p>
      <h2 className="mt-2 text-xl font-semibold tracking-tight text-[var(--ink)]">{title}</h2>
      <p className="mx-auto mt-2 max-w-lg text-sm text-[var(--muted)]">{description}</p>
      <p className="mx-auto mt-4 max-w-md text-sm text-[var(--muted)]">
        This surface will embed the dashboard built by {ownerLabel}. Set the embed URL in frontend
        env when ready.
      </p>
    </section>
  );
}
