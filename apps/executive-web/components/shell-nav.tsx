import Link from "next/link";

const LINKS = [
  { href: "/", label: "Overview" },
  { href: "/calendar", label: "Calendar" },
  { href: "/meetings", label: "Meetings" },
  { href: "/travel", label: "Travel" },
] as const;

export function ShellNav({ activeHref }: { activeHref: string }) {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-6 py-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-teal-700">WDTS</p>
          <h1 className="text-lg font-semibold tracking-tight text-slate-900">Executive</h1>
        </div>
        <nav className="flex flex-wrap gap-2">
          {LINKS.map((link) => {
            const active = activeHref === link.href;
            return (
              <Link
                className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition ${
                  active
                    ? "bg-teal-700 text-white"
                    : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                }`}
                href={link.href}
                key={link.href}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
