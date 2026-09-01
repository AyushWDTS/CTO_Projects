import { stringifyJson } from "@/lib/format";
import type { JsonValue } from "@/lib/types";

export function MetadataDisclosure({
  value,
  label = "Metadata",
}: {
  value?: JsonValue;
  label?: string;
}) {
  if (value === undefined || value === null) return <span className="text-slate-400">—</span>;

  return (
    <details className="rounded-md border border-slate-200 bg-slate-50">
      <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-slate-700">
        {label}
      </summary>
      <pre className="max-h-80 overflow-auto border-t border-slate-200 p-3 text-xs leading-5 text-slate-700">
        {stringifyJson(value)}
      </pre>
    </details>
  );
}
