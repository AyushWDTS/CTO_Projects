"use client";

type ConfirmRunModalProps = {
  open: boolean;
  dryRun: boolean;
  onCancel: () => void;
  onConfirm: () => void;
};

export function ConfirmRunModal({ open, dryRun, onCancel, onConfirm }: ConfirmRunModalProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl border border-[var(--line)] bg-[var(--surface)] p-5 shadow-lg">
        <h3 className="text-lg font-semibold text-[var(--ink)]">Confirm pipeline run</h3>
        <div className="mt-3 space-y-2 text-sm text-[var(--muted)]">
          <p>
            <span className="font-medium text-[var(--ink)]">Dry run:</span>{" "}
            {dryRun ? "ON" : "OFF"}
          </p>
          {!dryRun ? (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-amber-800">
              This run will write pipeline results to the database (ingestion through digest build).
              Proceed only if you intend to update live dashboard data.
            </p>
          ) : (
            <p>Dry run keeps the default safe mode for testing orchestration behavior.</p>
          )}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button
            className="rounded-lg border border-[var(--line)] px-3 py-2 text-sm font-medium"
            onClick={onCancel}
            type="button"
          >
            Cancel
          </button>
          <button
            className="rounded-lg bg-[var(--primary)] px-3 py-2 text-sm font-semibold text-white"
            onClick={onConfirm}
            type="button"
          >
            Confirm run
          </button>
        </div>
      </div>
    </div>
  );
}
