"use server";

import { revalidateTag } from "next/cache";
import { redirect } from "next/navigation";
import { DASHBOARD_DATA_CACHE_TAG } from "@/lib/db";

function safeReturnPath(value: FormDataEntryValue | null) {
  return value === "/?tab=gemini" ? "/?tab=gemini" : "/";
}

function withRefreshSuccess(path: string) {
  const [pathname, query = ""] = path.split("?", 2);
  const params = new URLSearchParams(query);
  params.set("refresh", "success");
  const queryString = params.toString();
  return queryString ? `${pathname}?${queryString}` : pathname;
}

export async function refreshDashboardData(formData: FormData) {
  revalidateTag(DASHBOARD_DATA_CACHE_TAG, { expire: 0 });
  redirect(withRefreshSuccess(safeReturnPath(formData.get("returnTo"))));
}

export async function refreshDashboardDataCache() {
  revalidateTag(DASHBOARD_DATA_CACHE_TAG, { expire: 0 });
}
