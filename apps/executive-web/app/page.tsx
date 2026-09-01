import { ShellNav } from "@/components/shell-nav";
import { SectionPanel } from "@/components/section-panel";

export default function OverviewPage() {
  return (
    <div>
      <ShellNav activeHref="/" />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <SectionPanel path="/overview" title="Overview" />
      </main>
    </div>
  );
}
