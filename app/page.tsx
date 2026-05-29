import { AlertTriangle, Bell, Bot, CheckCircle2, LayoutDashboard, RefreshCw, Search, Server, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { AutoRefreshDashboard } from "@/components/AutoRefreshDashboard";
import { LlmLogList } from "@/components/LlmLogList";
import { LatestFindingsSection, RecentRunsSection, SourceChecksSection } from "@/components/OverviewPaginatedSections";
import { getDashboardData } from "@/lib/db";
import { Footer } from "@/components/Footer";
import { refreshDashboardData } from "@/lib/actions";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type DashboardTab = "overview" | "gemini";
type StatTone = "teal" | "green" | "amber" | "rose" | "blue";

function formatDate(value: string | null) {
  if (!value) {
    return "Not finished";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function statusClasses(status: string) {
  const normalized = status.toLowerCase();
  if (normalized === "success") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (normalized === "failed") {
    return "border-rose-200 bg-rose-50 text-rose-700";
  }
  if (normalized === "partial_success") {
    return "border-amber-200 bg-amber-50 text-amber-700";
  }
  return "border-slate-200 bg-slate-50 text-slate-700";
}

function TabLink({ tab, activeTab, icon: Icon, children }: { tab: DashboardTab; activeTab: DashboardTab; icon: LucideIcon; children: ReactNode }) {
  const active = tab === activeTab;
  return (
    <a
      className={`inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-md border px-3 text-sm font-semibold transition sm:flex-none ${
        active
          ? "border-accent bg-accent text-white"
          : "border-line bg-white text-muted hover:border-accent hover:text-accent"
      }`}
      href={tab === "overview" ? "/" : `/?tab=${tab}`}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      {children}
    </a>
  );
}

const statToneClasses: Record<StatTone, { card: string; icon: string; iconColor: string; value: string; label: string }> = {
  teal: {
    card: "border-teal-100 bg-white",
    icon: "bg-teal-50",
    iconColor: "text-teal-700",
    value: "text-ink",
    label: "text-muted",
  },
  green: {
    card: "border-emerald-100 bg-white",
    icon: "bg-emerald-50",
    iconColor: "text-emerald-700",
    value: "text-ink",
    label: "text-muted",
  },
  amber: {
    card: "border-amber-100 bg-white",
    icon: "bg-amber-50",
    iconColor: "text-amber-700",
    value: "text-ink",
    label: "text-muted",
  },
  rose: {
    card: "border-rose-100 bg-white",
    icon: "bg-rose-50",
    iconColor: "text-rose-700",
    value: "text-ink",
    label: "text-muted",
  },
  blue: {
    card: "border-teal-700 bg-[#2f6f61]",
    icon: "bg-white/12",
    iconColor: "text-white",
    value: "text-white",
    label: "text-white/80",
  },
};

function StatCard({
  label,
  value,
  icon: Icon,
  tone,
  className = "",
}: {
  label: string;
  value: number | string;
  icon: LucideIcon;
  tone: StatTone;
  className?: string;
}) {
  const classes = statToneClasses[tone];

  return (
    <div className={`min-w-0 rounded-md border p-4 shadow-panel ${classes.card} ${className}`}>
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <div className={`font-heading text-sm font-medium ${classes.label}`}>{label}</div>
          <div className={`mt-2 break-words font-heading text-3xl font-semibold tracking-normal ${classes.value}`}>{value}</div>
        </div>
        <div className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${classes.icon}`}>
          <Icon className={`h-5 w-5 ${classes.iconColor}`} aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return <div className="px-4 py-8 text-sm text-muted">{message}</div>;
}

async function Dashboard({ activeTab }: { activeTab: DashboardTab }) {
  const data = await getDashboardData();
  const latestRun = data.runs[0];
  const returnTo = activeTab === "gemini" ? "/?tab=gemini" : "/";

  return (
    <>
      <AutoRefreshDashboard />
      <main className="min-h-screen">
        <header className="border-b border-line bg-white">
          <div className="mx-auto flex w-full max-w-7xl min-w-0 flex-col gap-3 px-4 py-5 sm:px-6 lg:px-8">
            <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
              <div>
                <h1 className="text-3xl font-semibold tracking-normal text-ink">ra-agent</h1>
                <p className="mt-1 text-sm text-muted">Scanner runs, source checks, findings, and notification counts from Supabase.</p>
              </div>
              <div className="flex items-center gap-2 md:justify-end">
                <div className="min-w-0 rounded-md bg-panel px-3 py-2 text-sm text-muted ring-1 ring-line">
                  Latest run: <span className="font-medium text-ink">{latestRun ? formatDate(latestRun.started_at) : "No runs yet"}</span>
                </div>
                <form action={refreshDashboardData}>
                  <input type="hidden" name="returnTo" value={returnTo} />
                  <button
                    className="inline-flex h-10 shrink-0 items-center gap-2 rounded-md border border-line bg-white px-3 text-sm font-semibold text-ink transition hover:border-accent hover:text-accent"
                    type="submit"
                  >
                    <RefreshCw className="h-4 w-4" aria-hidden="true" />
                    <span className="hidden min-[390px]:inline">Refresh</span>
                  </button>
                </form>
              </div>
            </div>
            <nav className="flex rounded-md bg-panel p-1 ring-1 ring-line sm:w-fit" aria-label="Dashboard menu">
              <div className="pr-1"><TabLink tab="overview" activeTab={activeTab} icon={LayoutDashboard}>Overview</TabLink></div>
              <TabLink tab="gemini" activeTab={activeTab} icon={Bot}>Gemini logs</TabLink>
            </nav>
          </div>
        </header>

        <div className="mx-auto grid w-full max-w-7xl min-w-0 gap-5 px-4 py-5 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            <StatCard label="Total runs" value={data.totals.totalRuns} icon={Server} tone="teal" />
            <StatCard label="Successful" value={data.totals.successfulRuns} icon={CheckCircle2} tone="green" />
            <StatCard label="Failed" value={data.totals.failedRuns} icon={XCircle} tone="rose" />
            {activeTab === "gemini" ? (
              <>
                <StatCard label="Gemini success" value={data.totals.llmSuccesses} icon={CheckCircle2} tone="amber" />
                <StatCard label="Gemini failed" value={data.totals.llmFailures} icon={XCircle} tone="blue" className="col-span-2 lg:col-span-1" />
              </>
            ) : (
              <>
                <StatCard label="Relevant posts" value={data.totals.relevantFindings} icon={Search} tone="amber" />
                <StatCard label="Notifications" value={data.totals.notificationsSent} icon={Bell} tone="blue" className="col-span-2 lg:col-span-1" />
              </>
            )}
          </div>

          {activeTab === "gemini" ? (
            !data.llmLogsAvailable ? (
              <section className="rounded-md border border-line bg-white shadow-panel">
                <EmptyState message="Gemini response logs are not available yet. Run the updated scanner once so it can create the llm_logs table in Supabase." />
              </section>
            ) : data.llmLogs.length ? (
              <LlmLogList logs={data.llmLogs} />
            ) : (
              <section className="rounded-md border border-line bg-white shadow-panel">
                <EmptyState message="No Gemini response logs have been captured yet. They will appear after the scanner runs with USE_LLM_CLASSIFIER=true." />
              </section>
            )
          ) : (
            <>
              <RecentRunsSection runs={data.runs} />

              <div className="grid gap-5 xl:grid-cols-[1fr_1.2fr]">
                <SourceChecksSection sourceLogs={data.sourceLogs} />
                <LatestFindingsSection findings={data.findings} />
              </div>
            </>
          )}
        </div>
      </main>
      <Footer />
    </>
  );
}

export default async function Home({ searchParams }: { searchParams: Promise<{ tab?: string }> }) {
  try {
    const params = await searchParams;
    const activeTab: DashboardTab = params.tab === "gemini" ? "gemini" : "overview";
    return await Dashboard({ activeTab });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unknown dashboard error.";

    return (
      <>
        <main className="flex min-h-screen items-center justify-center bg-panel px-4">
          <section className="w-full max-w-xl rounded-md border border-amber-200 bg-white p-6 shadow-panel">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-1 h-5 w-5 shrink-0 text-signal" aria-hidden="true" />
              <div>
                <h1 className="text-lg font-semibold text-ink">Dashboard cannot load logs</h1>
                <p className="mt-2 text-sm leading-6 text-muted">{message}</p>
                <p className="mt-4 text-sm leading-6 text-muted">Set `DATABASE_URL` in Vercel to the same Supabase Postgres connection string used by the scanner workflow.</p>
              </div>
            </div>
          </section>
        </main>
        <Footer />
      </>
    );
  }
}
