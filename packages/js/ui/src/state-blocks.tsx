export function LoadingState({ label = "Loading data" }: { label?: string }) {
  return (
    <div className="rounded-md border border-slate-200 bg-white p-6 text-sm text-slate-600">
      {label}…
    </div>
  );
}

export function EmptyState({ label = "No records found" }: { label?: string }) {
  return (
    <div className="rounded-md border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
      {label}
    </div>
  );
}

export function ErrorState({
  message,
  detail,
}: {
  message: string;
  detail?: string;
}) {
  return (
    <div className="rounded-md border border-red-200 bg-red-50 p-5 text-sm text-red-800">
      <p className="font-semibold">Unable to load data</p>
      <p className="mt-1">{message}</p>
      {detail ? <p className="mt-2 text-red-700">{detail}</p> : null}
    </div>
  );
}
