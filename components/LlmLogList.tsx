"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import type { LlmLog } from "@/lib/db";
import { LlmLogCard } from "@/components/LlmLogCard";

type Filter = "all" | "success" | "failed";

const PAGE_SIZE = 5;

function filterLabel(filter: Filter) {
  if (filter === "success") {
    return "Success";
  }
  if (filter === "failed") {
    return "Fail";
  }
  return "All";
}

function matchesFilter(log: LlmLog, filter: Filter) {
  if (filter === "all") {
    return true;
  }
  if (filter === "success") {
    return log.status.toLowerCase() === "success";
  }
  return log.status.toLowerCase() !== "success";
}

function FilterPill({
  filter,
  activeFilter,
  count,
  onClick,
}: {
  filter: Filter;
  activeFilter: Filter;
  count: number;
  onClick: () => void;
}) {
  const active = filter === activeFilter;

  return (
    <button
      className={`inline-flex h-9 items-center gap-2 rounded-full border px-3 text-sm font-semibold ${
        active
          ? "border-accent bg-accent text-white"
          : "border-line bg-white text-muted hover:border-accent hover:text-accent"
      }`}
      type="button"
      onClick={onClick}
    >
      {filterLabel(filter)}
      <span className={`rounded-full px-2 py-0.5 text-xs ${active ? "bg-white/20 text-white" : "bg-panel text-muted"}`}>{count}</span>
    </button>
  );
}

export function LlmLogList({ logs }: { logs: LlmLog[] }) {
  const [filter, setFilter] = useState<Filter>("all");
  const [page, setPage] = useState(1);

  const counts = useMemo(
    () => ({
      all: logs.length,
      success: logs.filter((log) => log.status.toLowerCase() === "success").length,
      failed: logs.filter((log) => log.status.toLowerCase() !== "success").length,
    }),
    [logs],
  );

  const filteredLogs = useMemo(() => logs.filter((log) => matchesFilter(log, filter)), [logs, filter]);
  const totalPages = Math.max(1, Math.ceil(filteredLogs.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const visibleLogs = filteredLogs.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  function selectFilter(nextFilter: Filter) {
    setFilter(nextFilter);
    setPage(1);
  }

  return (
    <section className="grid min-w-0 gap-3">
      <div className="flex flex-col gap-3 rounded-md border border-line bg-white p-3 shadow-panel sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap gap-2">
          <FilterPill filter="all" activeFilter={filter} count={counts.all} onClick={() => selectFilter("all")} />
          <FilterPill filter="success" activeFilter={filter} count={counts.success} onClick={() => selectFilter("success")} />
          <FilterPill filter="failed" activeFilter={filter} count={counts.failed} onClick={() => selectFilter("failed")} />
        </div>
        <div className="text-sm text-muted">
          Showing {visibleLogs.length ? (safePage - 1) * PAGE_SIZE + 1 : 0}-{Math.min(safePage * PAGE_SIZE, filteredLogs.length)} of {filteredLogs.length}
        </div>
      </div>

      {visibleLogs.length ? (
        visibleLogs.map((log) => <LlmLogCard key={log.id} log={log} />)
      ) : (
        <div className="rounded-md border border-line bg-white px-4 py-8 text-sm text-muted shadow-panel">No Gemini logs match this filter.</div>
      )}

      {totalPages > 1 ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-line bg-white p-3 shadow-panel">
          <button
            className="inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            onClick={() => setPage((value) => Math.max(1, value - 1))}
            disabled={safePage === 1}
          >
            <ChevronLeft className="h-4 w-4" aria-hidden="true" />
            <span className="hidden sm:inline">Previous</span>
          </button>
          <div className="text-sm font-medium text-muted">
            Page {safePage} of {totalPages}
          </div>
          <button
            className="inline-flex h-9 items-center gap-2 rounded-md border border-line px-3 text-sm font-semibold text-ink disabled:cursor-not-allowed disabled:opacity-50"
            type="button"
            onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
            disabled={safePage === totalPages}
          >
            <span className="hidden sm:inline">Next</span>
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      ) : null}
    </section>
  );
}
