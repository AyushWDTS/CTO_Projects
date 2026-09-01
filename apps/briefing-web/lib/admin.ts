"use client";

import { useEffect, useState } from "react";

export function isAdminEnabled(): boolean {
  return process.env.NEXT_PUBLIC_ADMIN_ENABLED === "true";
}

export function getRequiredAdminToken(): string | null {
  const token = process.env.NEXT_PUBLIC_ADMIN_TOKEN?.trim();
  return token || null;
}

export function hasAdminTokenAccess(): boolean {
  const required = getRequiredAdminToken();
  if (!required) return true;
  if (typeof window === "undefined") return false;
  return sessionStorage.getItem("admin_token") === required;
}

export function useAdminAccess(): { enabled: boolean; unlocked: boolean; ready: boolean } {
  const enabled = isAdminEnabled();
  const requiredToken = getRequiredAdminToken();
  const [unlocked, setUnlocked] = useState(!requiredToken);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!requiredToken) {
      setUnlocked(true);
    } else {
      setUnlocked(sessionStorage.getItem("admin_token") === requiredToken);
    }
    setReady(true);
  }, [requiredToken]);

  return { enabled, unlocked, ready };
}
