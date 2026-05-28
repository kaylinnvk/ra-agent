import { Pool } from "pg";

export type AgentRun = {
  id: number;
  started_at: string;
  finished_at: string | null;
  status: string;
  sources_checked: number;
  posts_found: number;
  new_posts: number;
  relevant_posts: number;
  notifications_sent: number;
  error_message: string | null;
};

export type SourceLog = {
  id: number;
  run_id: number | null;
  source_name: string;
  source_url: string;
  status: string;
  items_found: number;
  error_message: string | null;
  checked_at: string;
};

export type Finding = {
  id: number;
  run_id: number | null;
  title: string;
  url: string;
  source_name: string;
  is_relevant: boolean;
  relevance_score: number;
  reason: string | null;
  notified: boolean;
  created_at: string;
};

export type LlmLog = {
  id: number;
  run_id: number | null;
  title: string;
  url: string | null;
  provider: string;
  model: string;
  status: string;
  response_json: string | null;
  parsed_json: string | null;
  error_message: string | null;
  created_at: string;
};

export type DashboardData = {
  runs: AgentRun[];
  sourceLogs: SourceLog[];
  findings: Finding[];
  llmLogs: LlmLog[];
  llmLogsAvailable: boolean;
  totals: {
    totalRuns: number;
    successfulRuns: number;
    failedRuns: number;
    relevantFindings: number;
    notificationsSent: number;
    llmSuccesses: number;
    llmFailures: number;
  };
};

let pool: Pool | null = null;

function getPool() {
  const connectionString = process.env.DATABASE_URL;
  if (!connectionString) {
    throw new Error("DATABASE_URL is not configured.");
  }

  if (!pool) {
    pool = new Pool({
      connectionString,
      ssl: connectionString.includes("localhost") ? false : { rejectUnauthorized: false },
      max: 3,
    });
  }

  return pool;
}

function isMissingTableError(error: unknown) {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    (error as { code?: string }).code === "42P01"
  );
}

async function getLlmLogData(db: Pool) {
  try {
    const [logsResult, totalsResult] = await Promise.all([
      db.query<LlmLog>(
        `
        SELECT id, run_id, title, url, provider, model, status, response_json,
               parsed_json, error_message, created_at
        FROM llm_logs
        ORDER BY created_at DESC
        LIMIT 50
        `,
      ),
      db.query<{
        llm_successes: string;
        llm_failures: string;
      }>(
        `
        SELECT
          COUNT(*) FILTER (WHERE status = 'success')::text AS llm_successes,
          COUNT(*) FILTER (WHERE status != 'success')::text AS llm_failures
        FROM llm_logs
        `,
      ),
    ]);

    const totals = totalsResult.rows[0] ?? {
      llm_successes: "0",
      llm_failures: "0",
    };

    return {
      available: true,
      logs: logsResult.rows,
      successes: Number(totals.llm_successes),
      failures: Number(totals.llm_failures),
    };
  } catch (error) {
    if (!isMissingTableError(error)) {
      throw error;
    }

    return {
      available: false,
      logs: [],
      successes: 0,
      failures: 0,
    };
  }
}

export async function getDashboardData(): Promise<DashboardData> {
  const db = getPool();
  const [runsResult, sourceLogsResult, findingsResult, totalsResult, llmLogData] = await Promise.all([
    db.query<AgentRun>(
      `
      SELECT id, started_at, finished_at, status, sources_checked, posts_found,
             new_posts, relevant_posts, notifications_sent, error_message
      FROM agent_runs
      ORDER BY started_at DESC
      LIMIT 25
      `,
    ),
    db.query<SourceLog>(
      `
      SELECT id, run_id, source_name, source_url, status, items_found, error_message, checked_at
      FROM source_logs
      ORDER BY checked_at DESC
      LIMIT 25
      `,
    ),
    db.query<Finding>(
      `
      SELECT id, run_id, title, url, source_name, is_relevant, relevance_score,
             reason, notified, created_at
      FROM findings
      ORDER BY created_at DESC
      LIMIT 50
      `,
    ),
    db.query<{
      total_runs: string;
      successful_runs: string;
      failed_runs: string;
      relevant_findings: string;
      notifications_sent: string;
    }>(
      `
      SELECT
        COUNT(*)::text AS total_runs,
        COUNT(*) FILTER (WHERE status = 'success')::text AS successful_runs,
        COUNT(*) FILTER (WHERE status = 'failed')::text AS failed_runs,
        COALESCE(SUM(relevant_posts), 0)::text AS relevant_findings,
        COALESCE(SUM(notifications_sent), 0)::text AS notifications_sent
      FROM agent_runs
      `,
    ),
    getLlmLogData(db),
  ]);

  const totals = totalsResult.rows[0] ?? {
    total_runs: "0",
    successful_runs: "0",
    failed_runs: "0",
    relevant_findings: "0",
    notifications_sent: "0",
  };

  return {
    runs: runsResult.rows,
    sourceLogs: sourceLogsResult.rows,
    findings: findingsResult.rows,
    llmLogs: llmLogData.logs,
    llmLogsAvailable: llmLogData.available,
    totals: {
      totalRuns: Number(totals.total_runs),
      successfulRuns: Number(totals.successful_runs),
      failedRuns: Number(totals.failed_runs),
      relevantFindings: Number(totals.relevant_findings),
      notificationsSent: Number(totals.notifications_sent),
      llmSuccesses: llmLogData.successes,
      llmFailures: llmLogData.failures,
    },
  };
}
