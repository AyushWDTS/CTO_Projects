import Link from "next/link";
import { truncate } from "@/lib/format";

export function TruncatedText({
  value,
  length = 80,
}: {
  value?: string | null;
  length?: number;
}) {
  return <span title={value ?? undefined}>{truncate(value, length)}</span>;
}

export function ExternalLink({ href, label }: { href?: string | null; label?: string }) {
  if (!href) return <span className="text-slate-400">—</span>;
  return (
    <a
      className="text-teal-700 hover:text-teal-900 hover:underline"
      href={href}
      rel="noreferrer"
      target="_blank"
      title={href}
    >
      {truncate(label ?? href, 56)}
    </a>
  );
}

export function DetailLink({ href, label }: { href: string; label: string }) {
  return (
    <Link className="font-medium text-teal-700 hover:text-teal-900 hover:underline" href={href}>
      {label}
    </Link>
  );
}
