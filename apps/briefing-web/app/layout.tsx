import type { Metadata } from "next";
import Script from "next/script";
import { AppShell } from "@/components/app-shell";
import { WdtsShell } from "@/components/wdts-shell";
import "./portal-wdts-base.css";
import "./portal-wdts-aurora.css";
import "./portal-wdts-deepred.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "WDTS News Dashboard",
  description: "Daily WDTS news briefing and pipeline control dashboard.",
  icons: {
    icon: "/images/brand/favicon.ico",
  },
};

const themeInitScript = `(function () {
  try {
    var themeSetKey = "wdts.themeSet";
    var brandTokenKey = "wdts.brandToken";
    var validBrandTokens = {
      "deep-red": true,
      "orange": true,
      "gold": true,
      "teal": true,
      "purple": true,
      "charcoal": true
    };
    var params = new URLSearchParams(window.location.search || "");
    var brandTokenFromUrl = params.get("brandToken");
    var storedBrandToken = window.localStorage.getItem(brandTokenKey);
    var themeSet = "wdts-deepred-contrast";
    var brandToken = validBrandTokens[brandTokenFromUrl]
      ? brandTokenFromUrl
      : (validBrandTokens[storedBrandToken] ? storedBrandToken : "teal");

    window.localStorage.setItem(themeSetKey, themeSet);
    if (validBrandTokens[brandTokenFromUrl]) {
      window.localStorage.setItem(brandTokenKey, brandTokenFromUrl);
    }

    document.documentElement.setAttribute("data-theme-set", themeSet);
    document.documentElement.setAttribute("data-brand-token", brandToken);

    var stored = window.localStorage.getItem("wdts.theme");
    var sysDark = window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
    var theme = stored === "dark" || stored === "light"
      ? stored
      : (sysDark ? "dark" : "light");
    document.documentElement.setAttribute("data-theme", theme);
  } catch (_e) {
    document.documentElement.setAttribute("data-theme", "light");
    document.documentElement.setAttribute("data-theme-set", "wdts-deepred-contrast");
    document.documentElement.setAttribute("data-brand-token", "teal");
  }
})();`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>
        <Script
          dangerouslySetInnerHTML={{ __html: themeInitScript }}
          id="wdts-theme-init"
          strategy="beforeInteractive"
        />
        <WdtsShell>
          <AppShell>{children}</AppShell>
        </WdtsShell>
      </body>
    </html>
  );
}
