export const EMPTY_SECTION_MESSAGES: Record<string, string> = {
  "AI, ML & Computer Vision":
    "No AI / ML / computer vision signals in today's window. Coverage is partial — research and vendor feeds may still be catching up.",
  "Smart Tables & Casino Tech":
    "No smart-table or casino-tech signals in today's window. Supplier and lab sources may still be pending activation.",
  "Semiconductors & Components":
    "No semiconductor or component-supply signals in today's window. Chip and electronics coverage is partial.",
  "Automation & Operations Tech":
    "No automation or operations-tech signals in today's window.",
  "Competitors & Industry Watch":
    "No competitor or industry-watch signals in today's window.",
  "Regulation & Compliance":
    "No regulation or compliance signals in today's window.",
};

export function emptySectionMessage(sectionTitle: string): string {
  return (
    EMPTY_SECTION_MESSAGES[sectionTitle] ??
    "No significant items identified today."
  );
}
