"use server";

import { revalidateTag } from "next/cache";
import { redirect } from "next/navigation";
import { DASHBOARD_DATA_CACHE_TAG } from "@/lib/db";

function safeReturnPath(value: FormDataEntryValue | null) {
  return value === "/?tab=gemini" ? "/?tab=gemini" : "/";
}

export async function refreshDashboardData(formData: FormData) {
  revalidateTag(DASHBOARD_DATA_CACHE_TAG, { expire: 0 });
  redirect(safeReturnPath(formData.get("returnTo")));
}

export async function refreshDashboardDataCache() {
  revalidateTag(DASHBOARD_DATA_CACHE_TAG, { expire: 0 });
}
