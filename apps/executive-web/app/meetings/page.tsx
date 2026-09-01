import { ShellNav } from "@/components/shell-nav";
import { SectionPanel } from "@/components/section-panel";

export default function MeetingsPage() {
  return (
    <div>
      <ShellNav activeHref="/meetings" />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <SectionPanel path="/meetings" title="Meetings" />
      </main>
    </div>
  );
}
