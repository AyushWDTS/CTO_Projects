import { ShellNav } from "@/components/shell-nav";
import { SectionPanel } from "@/components/section-panel";

export default function CalendarPage() {
  return (
    <div>
      <ShellNav activeHref="/calendar" />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <SectionPanel path="/calendar" title="Calendar" />
      </main>
    </div>
  );
}
