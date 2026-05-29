"use client";

import { CheckCircle2 } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

export function RefreshToast() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [show, setShow] = useState(false);
  const refreshStatus = searchParams.get("refresh");

  useEffect(() => {
    if (refreshStatus !== "success") {
      return;
    }

    setShow(true);
    const hideTimer = window.setTimeout(() => setShow(false), 2200);
    const cleanupTimer = window.setTimeout(() => {
      const params = new URLSearchParams(searchParams.toString());
      params.delete("refresh");
      const queryString = params.toString();
      router.replace(queryString ? `${pathname}?${queryString}` : pathname, { scroll: false });
    }, 2700);

    return () => {
      window.clearTimeout(hideTimer);
      window.clearTimeout(cleanupTimer);
    };
  }, [pathname, refreshStatus, router, searchParams]);

  if (refreshStatus !== "success" && !show) {
    return null;
  }

  return (
    <div
      aria-live="polite"
      className={`fixed right-4 top-4 z-50 flex w-[calc(100vw-2rem)] max-w-sm items-center gap-3 rounded-md border border-emerald-200 bg-white px-4 py-3 text-sm text-ink shadow-lg transition-all duration-500 ease-out sm:right-6 sm:top-6 ${
        show ? "translate-x-0 opacity-100" : "translate-x-[120%] opacity-0"
      }`}
      role="status"
    >
      <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-600" aria-hidden="true" />
      <div className="min-w-0">
        <div className="font-semibold">Refresh complete</div>
        <div className="text-xs text-muted">Dashboard data is up to date.</div>
      </div>
    </div>
  );
}
