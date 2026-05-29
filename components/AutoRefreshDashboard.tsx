"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { refreshDashboardDataCache } from "@/lib/actions";

const SESSION_REFRESH_KEY = "ra-agent-dashboard-refreshed";

export function AutoRefreshDashboard() {
  const router = useRouter();

  useEffect(() => {
    if (sessionStorage.getItem(SESSION_REFRESH_KEY)) {
      return;
    }

    sessionStorage.setItem(SESSION_REFRESH_KEY, "true");
    refreshDashboardDataCache()
      .then(() => router.refresh())
      .catch(() => {
        sessionStorage.removeItem(SESSION_REFRESH_KEY);
      });
  }, [router]);

  return null;
}
