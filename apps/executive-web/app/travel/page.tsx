import { ShellNav } from "@/components/shell-nav";
import { SectionPanel } from "@/components/section-panel";

export default function TravelPage() {
  return (
    <div>
      <ShellNav activeHref="/travel" />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <SectionPanel path="/travel" title="Travel" />
      </main>
    </div>
  );
}
