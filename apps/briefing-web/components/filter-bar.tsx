"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

export type FilterField = {
  key: string;
  label: string;
  type?: "text" | "date" | "datetime-local" | "number" | "select";
  options?: { label: string; value: string }[];
};

export function FilterBar({ fields }: { fields: FilterField[] }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function updateFilter(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set(key, value);
    } else {
      params.delete(key);
    }
    params.set("offset", "0");
    router.push(`${pathname}?${params.toString()}`);
  }

  if (fields.length === 0) return null;

  return (
    <div className="grid gap-3 rounded-md border border-slate-200 bg-white p-3 sm:grid-cols-2 xl:grid-cols-4">
      {fields.map((field) => {
        const value = searchParams.get(field.key) ?? "";
        return (
          <label className="grid gap-1 text-xs font-medium text-slate-600" key={field.key}>
            {field.label}
            {field.type === "select" ? (
              <select
                className="rounded-md border border-slate-200 bg-white px-2 py-2 text-sm text-slate-800"
                onChange={(event) => updateFilter(field.key, event.target.value)}
                value={value}
              >
                <option value="">All</option>
                {field.options?.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            ) : (
              <input
                className="rounded-md border border-slate-200 px-2 py-2 text-sm text-slate-800"
                onChange={(event) => updateFilter(field.key, event.target.value)}
                type={field.type ?? "text"}
                value={value}
              />
            )}
          </label>
        );
      })}
    </div>
  );
}
