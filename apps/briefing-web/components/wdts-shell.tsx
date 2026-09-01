"use client";

import Script from "next/script";
import { type ReactNode, useEffect } from "react";

declare global {
  interface Window {
    WDTSShell?: {
      mount: (config: Record<string, unknown>) => void;
    };
  }
}

const SHELL_CONFIG = {
  headerHostId: "wdts-shell-header",
  footerHostId: "wdts-shell-footer",
  brandHref: "/cto",
  brandTitle: "Walker Digital",
  brandSubtitle: "CTO Dashboard",
  logoSrc: "/images/brand/logo-wdts-48x52.png",
  showUserLoginDetails: false,
  showThemeTokenPicker: false,
  footerText:
    "© WDTS, All rights reserved. Proprietary and confidential. Do not copy or distribute.",
};

function wireThemeToggle() {
  const toggle = document.getElementById("theme-toggle");
  if (!toggle || toggle.dataset.wired === "true") return;
  toggle.dataset.wired = "true";
  toggle.addEventListener("click", () => {
    const html = document.documentElement;
    const next = html.getAttribute("data-theme") === "dark" ? "light" : "dark";
    html.setAttribute("data-theme", next);
    localStorage.setItem("wdts.theme", next);
    toggle.setAttribute("aria-pressed", next === "dark" ? "true" : "false");
  });
}

export function WdtsShell({ children }: { children: ReactNode }) {
  useEffect(() => {
    if (window.WDTSShell) {
      window.WDTSShell.mount(SHELL_CONFIG);
      wireThemeToggle();
    }
  }, []);

  return (
    <>
      <Script
        onLoad={() => {
          window.WDTSShell?.mount(SHELL_CONFIG);
          wireThemeToggle();
        }}
        src="/js/wdts-shell.js"
        strategy="afterInteractive"
      />
      <div className="portal is-sidebar-collapsed" id="portal-root">
        <div id="wdts-shell-header" />
        <main className="portal__main" id="main-content">
          {children}
        </main>
        <div id="wdts-shell-footer" />
      </div>
    </>
  );
}
