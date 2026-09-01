import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WDTS Executive",
  description: "Calendar, meetings, and travel for CTO leadership.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
