import { AlertTriangle, Bell, Bot, CheckCircle2, ExternalLink, LayoutDashboard, Search, Server, XCircle } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { getDashboardData, type AgentRun, type Finding, type LlmLog, type SourceLog } from "@/lib/db";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type DashboardTab = "overview" | "gemini";

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

function llmCardClasses(status: string) {
  if (status.toLowerCase() === "success") {
    return "border-emerald-200 bg-emerald-50";
  }
  return "border-rose-200 bg-rose-50";
}

function prettifyJson(value: string | null) {
  if (!value) {
    return "";
  }
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
}

function TabLink({ tab, activeTab, icon: Icon, children }: { tab: DashboardTab; activeTab: DashboardTab; icon: LucideIcon; children: ReactNode }) {
  const active = tab === activeTab;
  return (
    <a
      className={`inline-flex h-10 items-center gap-2 rounded-md border px-3 text-sm font-semibold transition ${
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

function StatCard({ label, value, icon: Icon, className = "" }: { label: string; value: number | string; icon: LucideIcon; className?: string }) {
  return (
    <div className={`rounded-md border border-line bg-white p-4 shadow-panel ${className}`}>
      <div className="flex items-center justify-between gap-3">
        <span className="text-sm font-medium text-muted">{label}</span>
        <Icon className="h-4 w-4 text-accent" aria-hidden="true" />
      </div>
      <div className="mt-2 text-3xl font-semibold tracking-normal text-ink">{value}</div>
    </div>
  );
}

function RunRow({ run }: { run: AgentRun }) {
  return (
    <tr className="border-b border-line last:border-0">
      <td className="whitespace-nowrap px-4 py-3 font-medium text-ink">#{run.id}</td>
      <td className="whitespace-nowrap px-4 py-3 text-muted">{formatDate(run.started_at)}</td>
      <td className="px-4 py-3">
        <span className={`inline-flex rounded-md border px-2 py-1 text-xs font-semibold ${statusClasses(run.status)}`}>{run.status}</span>
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-right">{run.posts_found}</td>
      <td className="whitespace-nowrap px-4 py-3 text-right">{run.new_posts}</td>
      <td className="whitespace-nowrap px-4 py-3 text-right">{run.relevant_posts}</td>
      <td className="whitespace-nowrap px-4 py-3 text-right">{run.notifications_sent}</td>
      <td className="max-w-[20rem] px-4 py-3 text-sm text-rose-700">{run.error_message || ""}</td>
    </tr>
  );
}

function SourceLogRow({ log }: { log: SourceLog }) {
  return (
    <tr className="border-b border-line last:border-0">
      <td className="whitespace-nowrap px-4 py-3 text-muted">{formatDate(log.checked_at)}</td>
      <td className="px-4 py-3">
        <span className={`inline-flex rounded-md border px-2 py-1 text-xs font-semibold ${statusClasses(log.status)}`}>{log.status}</span>
      </td>
      <td className="max-w-[22rem] px-4 py-3">
        <a className="inline-flex items-center gap-1 font-medium text-ink hover:text-accent" href={log.source_url} target="_blank" rel="noreferrer">
          <span className="truncate">{log.source_name}</span>
          <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        </a>
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-right">{log.items_found}</td>
      <td className="max-w-[24rem] px-4 py-3 text-sm text-rose-700">{log.error_message || ""}</td>
    </tr>
  );
}

function FindingRow({ finding }: { finding: Finding }) {
  return (
    <tr className="border-b border-line last:border-0">
      <td className="whitespace-nowrap px-4 py-3 text-muted">{formatDate(finding.created_at)}</td>
      <td className="max-w-[28rem] px-4 py-3">
        <a className="inline-flex items-center gap-1 font-medium text-ink hover:text-accent" href={finding.url} target="_blank" rel="noreferrer">
          <span>{finding.title}</span>
          <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
        </a>
        {finding.reason ? <div className="mt-1 line-clamp-2 text-sm text-muted">{finding.reason}</div> : null}
      </td>
      <td className="px-4 py-3">
        <span className={`inline-flex rounded-md border px-2 py-1 text-xs font-semibold ${finding.is_relevant ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-slate-50 text-slate-700"}`}>
          {finding.is_relevant ? "Relevant" : "Filtered"}
        </span>
      </td>
      <td className="whitespace-nowrap px-4 py-3 text-right">{finding.relevance_score}</td>
      <td className="whitespace-nowrap px-4 py-3 text-right">{finding.notified ? "Yes" : "No"}</td>
    </tr>
  );
}

function LlmLogCard({ log }: { log: LlmLog }) {
  const success = log.status.toLowerCase() === "success";
  const responseText = success ? prettifyJson(log.parsed_json || log.response_json) : log.error_message || "No error details captured.";

  return (
    <article className={`rounded-md border p-4 shadow-panel ${llmCardClasses(log.status)}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${success ? "border-emerald-300 bg-white text-emerald-700" : "border-rose-300 bg-white text-rose-700"}`}>
              {success ? "Success" : "Failed"}
            </span>
            <span className="text-xs font-medium uppercase text-muted">{log.provider} / {log.model}</span>
          </div>
          <h3 className="mt-3 text-base font-semibold text-ink">{log.title}</h3>
          <div className="mt-1 text-sm text-muted">{formatDate(log.created_at)}{log.run_id ? ` - Run #${log.run_id}` : ""}</div>
        </div>
        {log.url ? (
          <a className="inline-flex items-center gap-1 text-sm font-semibold text-accent hover:text-ink" href={log.url} target="_blank" rel="noreferrer">
            Source
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        ) : null}
      </div>
      <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap rounded-md border border-white/70 bg-white/80 p-3 text-xs leading-5 text-ink">
        {responseText}
      </pre>
    </article>
  );
}

function CompactRunCard({ run }: { run: AgentRun }) {
  return (
    <article className="rounded-md border border-line bg-white p-4 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <span className="font-semibold text-ink">Run #{run.id}</span>
        <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${statusClasses(run.status)}`}>{run.status}</span>
      </div>
      <div className="mt-2 text-sm text-muted">{formatDate(run.started_at)}</div>
      <div className="mt-3 grid grid-cols-4 gap-2 text-center text-sm">
        <div><div className="font-semibold text-ink">{run.posts_found}</div><div className="text-xs text-muted">Found</div></div>
        <div><div className="font-semibold text-ink">{run.new_posts}</div><div className="text-xs text-muted">New</div></div>
        <div><div className="font-semibold text-ink">{run.relevant_posts}</div><div className="text-xs text-muted">Relevant</div></div>
        <div><div className="font-semibold text-ink">{run.notifications_sent}</div><div className="text-xs text-muted">Sent</div></div>
      </div>
      {run.error_message ? <p className="mt-3 text-sm text-rose-700">{run.error_message}</p> : null}
    </article>
  );
}

function CompactFindingCard({ finding }: { finding: Finding }) {
  return (
    <article className="rounded-md border border-line bg-white p-4 shadow-panel">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${finding.is_relevant ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-slate-50 text-slate-700"}`}>
          {finding.is_relevant ? "Relevant" : "Filtered"}
        </span>
        <span className="text-xs text-muted">Score {finding.relevance_score}</span>
        <span className="text-xs text-muted">{formatDate(finding.created_at)}</span>
      </div>
      <a className="mt-3 inline-flex items-center gap-1 font-semibold text-ink hover:text-accent" href={finding.url} target="_blank" rel="noreferrer">
        {finding.title}
        <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      </a>
      {finding.reason ? <p className="mt-2 text-sm text-muted">{finding.reason}</p> : null}
    </article>
  );
}

function CompactSourceLogCard({ log }: { log: SourceLog }) {
  return (
    <article className="rounded-md border border-line bg-white p-4 shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${statusClasses(log.status)}`}>{log.status}</span>
        <span className="text-xs text-muted">{formatDate(log.checked_at)}</span>
      </div>
      <a className="mt-3 inline-flex items-center gap-1 font-semibold text-ink hover:text-accent" href={log.source_url} target="_blank" rel="noreferrer">
        {log.source_name}
        <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      </a>
      <div className="mt-2 text-sm text-muted">Items found: <span className="font-semibold text-ink">{log.items_found}</span></div>
      {log.error_message ? <p className="mt-2 text-sm text-rose-700">{log.error_message}</p> : null}
    </article>
  );
}

function TableShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-md border border-line bg-white shadow-panel">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold text-ink">{title}</h2>
      </div>
      <div className="overflow-x-auto">{children}</div>
    </section>
  );
}

function EmptyState({ message }: { message: string }) {
  return <div className="px-4 py-8 text-sm text-muted">{message}</div>;
}

async function Dashboard({ activeTab }: { activeTab: DashboardTab }) {
  const data = await getDashboardData();
  const latestRun = data.runs[0];

  return (
    <main className="min-h-screen">
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 py-5 sm:px-6 lg:px-8">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="text-2xl font-semibold tracking-normal text-ink">RA Agent Logs</h1>
              <p className="mt-1 text-sm text-muted">Scanner runs, source checks, findings, and notification counts from Supabase.</p>
            </div>
            <div className="rounded-md border border-line bg-panel px-3 py-2 text-sm text-muted">
              Latest run: <span className="font-medium text-ink">{latestRun ? formatDate(latestRun.started_at) : "No runs yet"}</span>
            </div>
          </div>
          <nav className="flex flex-wrap gap-2" aria-label="Dashboard menu">
            <TabLink tab="overview" activeTab={activeTab} icon={LayoutDashboard}>Overview</TabLink>
            <TabLink tab="gemini" activeTab={activeTab} icon={Bot}>Gemini logs</TabLink>
          </nav>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
          <StatCard label="Total runs" value={data.totals.totalRuns} icon={Server} />
          <StatCard label="Successful" value={data.totals.successfulRuns} icon={CheckCircle2} />
          <StatCard label="Failed" value={data.totals.failedRuns} icon={XCircle} />
          {activeTab === "gemini" ? (
            <>
              <StatCard label="Gemini success" value={data.totals.llmSuccesses} icon={CheckCircle2} />
              <StatCard label="Gemini failed" value={data.totals.llmFailures} icon={XCircle} className="col-span-2 lg:col-span-1" />
            </>
          ) : (
            <>
              <StatCard label="Relevant posts" value={data.totals.relevantFindings} icon={Search} />
              <StatCard label="Notifications" value={data.totals.notificationsSent} icon={Bell} className="col-span-2 lg:col-span-1" />
            </>
          )}
        </div>

        {activeTab === "gemini" ? (
          !data.llmLogsAvailable ? (
            <section className="rounded-md border border-line bg-white shadow-panel">
              <EmptyState message="Gemini response logs are not available yet. Run the updated scanner once so it can create the llm_logs table in Supabase." />
            </section>
          ) : data.llmLogs.length ? (
            <section className="grid gap-3">
              {data.llmLogs.map((log) => <LlmLogCard key={log.id} log={log} />)}
            </section>
          ) : (
            <section className="rounded-md border border-line bg-white shadow-panel">
              <EmptyState message="No Gemini response logs have been captured yet. They will appear after the scanner runs with USE_LLM_CLASSIFIER=true." />
            </section>
          )
        ) : (
          <>
            <TableShell title="Recent Runs">
              {data.runs.length ? (
                <>
                  <div className="grid gap-3 p-3 md:hidden">
                    {data.runs.map((run) => <CompactRunCard key={run.id} run={run} />)}
                  </div>
                  <table className="hidden w-full min-w-[58rem] text-left text-sm md:table">
                    <thead className="bg-panel text-xs uppercase text-muted">
                      <tr>
                        <th className="px-4 py-3">Run</th>
                        <th className="px-4 py-3">Started</th>
                        <th className="px-4 py-3">Status</th>
                        <th className="px-4 py-3 text-right">Found</th>
                        <th className="px-4 py-3 text-right">New</th>
                        <th className="px-4 py-3 text-right">Relevant</th>
                        <th className="px-4 py-3 text-right">Sent</th>
                        <th className="px-4 py-3">Error</th>
                      </tr>
                    </thead>
                    <tbody>{data.runs.map((run) => <RunRow key={run.id} run={run} />)}</tbody>
                  </table>
                </>
              ) : (
                <EmptyState message="No scanner runs have been logged yet." />
              )}
            </TableShell>

            <div className="grid gap-5 xl:grid-cols-[1fr_1.2fr]">
              <TableShell title="Source Checks">
                {data.sourceLogs.length ? (
                  <>
                    <div className="grid gap-3 p-3 md:hidden">
                      {data.sourceLogs.map((log) => <CompactSourceLogCard key={log.id} log={log} />)}
                    </div>
                    <table className="hidden w-full min-w-[48rem] text-left text-sm md:table">
                      <thead className="bg-panel text-xs uppercase text-muted">
                        <tr>
                          <th className="px-4 py-3">Checked</th>
                          <th className="px-4 py-3">Status</th>
                          <th className="px-4 py-3">Source</th>
                          <th className="px-4 py-3 text-right">Items</th>
                          <th className="px-4 py-3">Error</th>
                        </tr>
                      </thead>
                      <tbody>{data.sourceLogs.map((log) => <SourceLogRow key={log.id} log={log} />)}</tbody>
                    </table>
                  </>
                ) : (
                  <EmptyState message="No source checks have been logged yet." />
                )}
              </TableShell>

              <TableShell title="Latest Findings">
                {data.findings.length ? (
                  <>
                    <div className="grid gap-3 p-3 md:hidden">
                      {data.findings.map((finding) => <CompactFindingCard key={finding.id} finding={finding} />)}
                    </div>
                    <table className="hidden w-full min-w-[54rem] text-left text-sm md:table">
                      <thead className="bg-panel text-xs uppercase text-muted">
                        <tr>
                          <th className="px-4 py-3">Created</th>
                          <th className="px-4 py-3">Finding</th>
                          <th className="px-4 py-3">Result</th>
                          <th className="px-4 py-3 text-right">Score</th>
                          <th className="px-4 py-3 text-right">Notified</th>
                        </tr>
                      </thead>
                      <tbody>{data.findings.map((finding) => <FindingRow key={finding.id} finding={finding} />)}</tbody>
                    </table>
                  </>
                ) : (
                  <EmptyState message="No findings have been logged yet." />
                )}
              </TableShell>
            </div>
          </>
        )}
      </div>
    </main>
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
    );
  }
}
