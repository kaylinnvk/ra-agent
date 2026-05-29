"use client";

import { ChevronDown, ChevronUp, Clock3, ExternalLink, FlaskConical, Tag } from "lucide-react";
import { useMemo, useState } from "react";
import type { LlmLog } from "@/lib/db";

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

function cardClasses(status: string) {
  return status.toLowerCase() === "success"
    ? "border-line bg-white"
    : "border-rose-200 bg-white";
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

function parseJson(value: string | null): Record<string, unknown> | null {
  if (!value) {
    return null;
  }
  try {
    const parsed = JSON.parse(value);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : null;
  } catch {
    return null;
  }
}

function textValue(value: unknown) {
  if (Array.isArray(value)) {
    return value.map(String).join(", ");
  }
  if (value === null || value === undefined || value === "") {
    return "Not provided";
  }
  return String(value);
}

function shortModelName(model: string) {
  return model
    .replace(/^gemini-/i, "Gemini ")
    .replace(/-/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function keywordValues(value: unknown) {
  if (Array.isArray(value)) {
    return value.map(String).filter(Boolean);
  }
  if (typeof value === "string" && value.trim()) {
    return value.split(",").map((part) => part.trim()).filter(Boolean);
  }
  return [];
}

function Pill({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "blue" }) {
  return (
    <span className={`inline-flex min-h-8 items-center gap-1.5 rounded-full border px-3 py-1 text-sm font-medium ${
      tone === "blue"
        ? "border-blue-200 bg-blue-50 text-blue-700"
        : "border-line bg-panel text-ink"
    }`}>
      {children}
    </span>
  );
}

function SuccessSummary({ parsed }: { parsed: Record<string, unknown> | null }) {
  if (!parsed) {
    return <p className="mt-3 text-sm text-muted">Gemini returned a successful response.</p>;
  }

  const fitScore = textValue(parsed.fit_score);
  const isRaOpening = parsed.is_ra_opening === true ? "RA opening" : "Not RA opening";
  const deadline = textValue(parsed.deadline) === "Not provided" ? "No deadline" : textValue(parsed.deadline);
  const keywords = keywordValues(parsed.matched_keywords);

  return (
    <>
      <div className="mt-2 flex flex-wrap gap-2">
        <Pill tone="blue">Fit {fitScore}/10</Pill>
        <Pill><FlaskConical className="h-4 w-4" aria-hidden="true" />{isRaOpening}</Pill>
        <Pill><Clock3 className="h-4 w-4" aria-hidden="true" />{deadline}</Pill>
        <Pill>{textValue(parsed.professor_group)}</Pill>
        <Pill><Tag className="h-4 w-4" aria-hidden="true" />{textValue(parsed.topic_area)}</Pill>
      </div>

      <div className="mt-4 border-t border-line pt-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-muted">Why relevant</div>
        <p className="mt-1 text-sm leading-6 text-ink">{textValue(parsed.why_relevant)}</p>
      </div>

      {keywords.length ? (
        <div className="mt-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-muted">Matched keywords</div>
          <div className="mt-2 flex flex-wrap gap-2">
            {keywords.map((keyword) => (
              <span key={keyword} className="rounded-full border border-line bg-panel px-2.5 py-1 text-xs font-medium text-ink">
                {keyword}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </>
  );
}

function FailureSummary({ errorMessage }: { errorMessage: string | null }) {
  const parsedError = parseJson(errorMessage);
  const statusCode = parsedError?.status_code;
  const message = parsedError?.message ?? errorMessage ?? "No error summary captured.";

  return (
    <div className="mt-3 rounded-md border border-rose-100 bg-rose-50 p-3">
      <div className="text-xs font-semibold uppercase text-muted">Error summary</div>
      <p className="mt-1 text-sm text-ink [overflow-wrap:anywhere]">{textValue(message)}</p>
      {statusCode ? <p className="mt-2 text-xs font-semibold text-rose-700">HTTP {textValue(statusCode)}</p> : null}
    </div>
  );
}

export function LlmLogCard({ log }: { log: LlmLog }) {
  const [expanded, setExpanded] = useState(false);
  const success = log.status.toLowerCase() === "success";
  const parsed = useMemo(() => parseJson(log.parsed_json), [log.parsed_json]);
  const detailsText = success
    ? prettifyJson(log.parsed_json || log.response_json)
    : prettifyJson(log.error_message);

  return (
    <article className={`min-w-0 overflow-hidden rounded-md border p-4 shadow-panel sm:p-5 ${cardClasses(log.status)}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
            <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${success ? "border-emerald-200 bg-emerald-100 text-emerald-800" : "border-rose-200 bg-rose-100 text-rose-800"}`}>
              {success ? "Success" : "Failed"}
            </span>
            <span className="font-medium">{shortModelName(log.model)}</span>
            {log.run_id ? <span>Run #{log.run_id}</span> : null}
            <span>{formatDate(log.created_at)}</span>
          </div>
          <h3 className="mt-3 break-words text-lg font-semibold leading-snug text-ink">{log.title}</h3>
        </div>
        {log.url ? (
          <a className="inline-flex items-center gap-1 text-sm font-semibold text-accent hover:text-ink" href={log.url} target="_blank" rel="noreferrer">
            Source
            <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        ) : null}
      </div>

      {success ? <SuccessSummary parsed={parsed} /> : <FailureSummary errorMessage={log.error_message} />}

      <button
        className="mt-4 inline-flex h-10 items-center gap-2 rounded-md border border-line bg-white px-4 text-sm font-semibold text-ink hover:border-accent hover:text-accent"
        type="button"
        onClick={() => setExpanded((value) => !value)}
        aria-expanded={expanded}
      >
        {expanded ? <ChevronUp className="h-4 w-4" aria-hidden="true" /> : <ChevronDown className="h-4 w-4" aria-hidden="true" />}
        {expanded ? "Hide details" : "More details"}
      </button>

      {expanded ? (
        <pre className="mt-3 max-h-80 overflow-auto whitespace-pre-wrap rounded-md border border-white/70 bg-white/80 p-3 text-xs leading-5 text-ink [overflow-wrap:anywhere]">
          {detailsText || "No details captured."}
        </pre>
      ) : null}
    </article>
  );
}
