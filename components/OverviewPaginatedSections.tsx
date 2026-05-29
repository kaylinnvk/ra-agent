"use client";

import { CheckCircle2, ChevronLeft, ChevronRight, ExternalLink, XCircle } from "lucide-react";
import { useState } from "react";
import type { AgentRun, Finding, SourceLog } from "@/lib/db";

const PAGE_SIZE = 5;

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

function PaginationControls({
  page,
  totalPages,
  totalItems,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  totalItems: number;
  onPageChange: (page: number) => void;
}) {
  if (totalPages <= 1) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-white p-3">
      <button
        className="inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-50"
        type="button"
        onClick={() => onPageChange(Math.max(1, page - 1))}
        disabled={page === 1}
      >
        <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        <span className="hidden sm:inline">Previous</span>
      </button>
      <div className="text-sm font-medium text-muted">
        Page {page} of {totalPages} · {totalItems} total
      </div>
      <button
        className="inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-50"
        type="button"
        onClick={() => onPageChange(Math.min(totalPages, page + 1))}
        disabled={page === totalPages}
      >
        <span className="hidden sm:inline">Next</span>
        <ChevronRight className="h-4 w-4" aria-hidden="true" />
      </button>
    </div>
  );
}

function usePage<T>(items: T[]) {
  const [page, setPage] = useState(1);
  const totalPages = Math.max(1, Math.ceil(items.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const visibleItems = items.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  return { page: safePage, totalPages, visibleItems, setPage };
}

function SectionShell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="min-w-0 overflow-hidden rounded-md border border-line bg-white shadow-panel">
      <div className="border-b border-line px-4 py-3">
        <h2 className="text-base font-semibold text-ink">{title}</h2>
      </div>
      {children}
    </section>
  );
}

function EmptyState({ message }: { message: string }) {
  return <div className="px-4 py-8 text-sm text-muted">{message}</div>;
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
      <td className="max-w-[20rem] break-words px-4 py-3 text-sm text-rose-700 [overflow-wrap:anywhere]">{run.error_message || ""}</td>
    </tr>
  );
}

function CompactRunCard({ run }: { run: AgentRun }) {
  const success = run.status.toLowerCase() === "success";

  return (
    <article className="min-w-0 overflow-hidden rounded-md border border-line bg-white p-4 shadow-panel">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1">
          <span className="break-words text-lg font-semibold text-ink">Run #{run.id}</span>
          <span className="text-sm font-medium text-muted">{formatDate(run.started_at)}</span>
        </div>
        <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold ${success ? "border-emerald-100 bg-emerald-50 text-emerald-800" : statusClasses(run.status)}`}>
          {success ? <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> : <XCircle className="h-3.5 w-3.5" aria-hidden="true" />}
          {run.status}
        </span>
      </div>
      <div className="mt-4 border-t border-line pt-4">
        <div className="grid grid-cols-4 gap-1.5 text-center text-sm min-[390px]:gap-2">
          <div className="min-w-0 rounded-md bg-panel px-1.5 py-3"><div className="text-lg font-semibold text-accent min-[390px]:text-xl">{run.posts_found}</div><div className="text-[11px] font-medium text-muted min-[390px]:text-xs">Found</div></div>
          <div className="min-w-0 rounded-md bg-panel px-1.5 py-3"><div className="text-lg font-semibold text-accent min-[390px]:text-xl">{run.new_posts}</div><div className="text-[11px] font-medium text-muted min-[390px]:text-xs">New</div></div>
          <div className="min-w-0 rounded-md bg-panel px-1.5 py-3"><div className="text-lg font-semibold text-ink min-[390px]:text-xl">{run.relevant_posts}</div><div className="text-[11px] font-medium text-muted min-[390px]:text-xs">Relevant</div></div>
          <div className="min-w-0 rounded-md bg-panel px-1.5 py-3"><div className="text-lg font-semibold text-ink min-[390px]:text-xl">{run.notifications_sent}</div><div className="text-[11px] font-medium text-muted min-[390px]:text-xs">Sent</div></div>
        </div>
      </div>
      {run.error_message ? <p className="mt-3 break-words text-sm text-rose-700 [overflow-wrap:anywhere]">{run.error_message}</p> : null}
    </article>
  );
}

export function RecentRunsSection({ runs }: { runs: AgentRun[] }) {
  const { page, totalPages, visibleItems, setPage } = usePage(runs);

  return (
    <SectionShell title="Recent Runs">
      {runs.length ? (
        <>
          <div className="grid gap-3 p-3 md:hidden">
            {visibleItems.map((run) => <CompactRunCard key={run.id} run={run} />)}
          </div>
          <div className="min-w-0 overflow-x-auto">
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
              <tbody>{visibleItems.map((run) => <RunRow key={run.id} run={run} />)}</tbody>
            </table>
          </div>
          <PaginationControls page={page} totalPages={totalPages} totalItems={runs.length} onPageChange={setPage} />
        </>
      ) : (
        <EmptyState message="No scanner runs have been logged yet." />
      )}
    </SectionShell>
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
      <td className="max-w-[24rem] break-words px-4 py-3 text-sm text-rose-700 [overflow-wrap:anywhere]">{log.error_message || ""}</td>
    </tr>
  );
}

function CompactSourceLogCard({ log }: { log: SourceLog }) {
  return (
    <article className="min-w-0 overflow-hidden rounded-md border border-line bg-white p-4 shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${statusClasses(log.status)}`}>{log.status}</span>
        <span className="text-xs text-muted">{formatDate(log.checked_at)}</span>
      </div>
      <a className="mt-3 flex min-w-0 items-start gap-1 font-semibold text-ink hover:text-accent" href={log.source_url} target="_blank" rel="noreferrer">
        <span className="min-w-0 break-words [overflow-wrap:anywhere]">{log.source_name}</span>
        <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      </a>
      <div className="mt-2 text-sm text-muted">Items found: <span className="font-semibold text-ink">{log.items_found}</span></div>
      {log.error_message ? <p className="mt-2 break-words text-sm text-rose-700 [overflow-wrap:anywhere]">{log.error_message}</p> : null}
    </article>
  );
}

export function SourceChecksSection({ sourceLogs }: { sourceLogs: SourceLog[] }) {
  const { page, totalPages, visibleItems, setPage } = usePage(sourceLogs);

  return (
    <SectionShell title="Source Checks">
      {sourceLogs.length ? (
        <>
          <div className="grid gap-3 p-3 md:hidden">
            {visibleItems.map((log) => <CompactSourceLogCard key={log.id} log={log} />)}
          </div>
          <div className="min-w-0 overflow-x-auto">
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
              <tbody>{visibleItems.map((log) => <SourceLogRow key={log.id} log={log} />)}</tbody>
            </table>
          </div>
          <PaginationControls page={page} totalPages={totalPages} totalItems={sourceLogs.length} onPageChange={setPage} />
        </>
      ) : (
        <EmptyState message="No source checks have been logged yet." />
      )}
    </SectionShell>
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

function CompactFindingCard({ finding }: { finding: Finding }) {
  return (
    <article className="min-w-0 overflow-hidden rounded-md border border-line bg-white p-4 shadow-panel">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`rounded-md border px-2 py-1 text-xs font-semibold ${finding.is_relevant ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-slate-200 bg-slate-50 text-slate-700"}`}>
          {finding.is_relevant ? "Relevant" : "Filtered"}
        </span>
        <span className="text-xs text-muted">Score {finding.relevance_score}</span>
        <span className="text-xs text-muted">{formatDate(finding.created_at)}</span>
      </div>
      <a className="mt-3 flex min-w-0 items-start gap-1 font-semibold text-ink hover:text-accent" href={finding.url} target="_blank" rel="noreferrer">
        <span className="min-w-0 break-words [overflow-wrap:anywhere]">{finding.title}</span>
        <ExternalLink className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      </a>
      {finding.reason ? <p className="mt-2 break-words text-sm text-muted [overflow-wrap:anywhere]">{finding.reason}</p> : null}
    </article>
  );
}

export function LatestFindingsSection({ findings }: { findings: Finding[] }) {
  const { page, totalPages, visibleItems, setPage } = usePage(findings);

  return (
    <SectionShell title="Latest Findings">
      {findings.length ? (
        <>
          <div className="grid gap-3 p-3 md:hidden">
            {visibleItems.map((finding) => <CompactFindingCard key={finding.id} finding={finding} />)}
          </div>
          <div className="min-w-0 overflow-x-auto">
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
              <tbody>{visibleItems.map((finding) => <FindingRow key={finding.id} finding={finding} />)}</tbody>
            </table>
          </div>
          <PaginationControls page={page} totalPages={totalPages} totalItems={findings.length} onPageChange={setPage} />
        </>
      ) : (
        <EmptyState message="No findings have been logged yet." />
      )}
    </SectionShell>
  );
}
