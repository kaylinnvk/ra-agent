import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.config import settings

LEGACY_TABLE_NAME = "opportunities"
DYNAMIC_HASH_LABELS = {
    "status",
    "view_count",
    "views",
    "applicant_count",
    "accepted_count",
    "has_applied",
    "posted_date",
    "last_seen_at",
    "checked_at",
}


def compute_content_hash(title: str, snippet: str = "") -> str:
    normalized_title = " ".join((title or "").split()).strip().lower()
    normalized_snippet = _stable_snippet_for_hash(snippet)
    payload = f"{normalized_title}\n{normalized_snippet}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _stable_snippet_for_hash(snippet: str = "") -> str:
    stable_parts: list[str] = []
    for part in (snippet or "").split("|"):
        clean = " ".join(part.split()).strip()
        if not clean:
            continue
        label = clean.split(":", 1)[0].strip().lower()
        if label in DYNAMIC_HASH_LABELS:
            continue
        stable_parts.append(clean.lower())
    return " | ".join(stable_parts)


def normalize_url(url: str) -> str:
    parsed = urlsplit((url or "").strip())
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)), doseq=True)
    return urlunsplit((scheme, netloc, path, query, ""))


def db_backend() -> str:
    if settings.db_backend == "postgres" and settings.database_url:
        return "postgres"
    return "sqlite"


def _sqlite_path() -> Path:
    return Path(settings.sqlite_path)


@contextmanager
def _connect() -> Iterator[Any]:
    if db_backend() == "postgres":
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "Postgres backend requires psycopg. Install requirements.txt first."
            ) from exc

        with psycopg.connect(settings.database_url) as conn:
            yield conn
        return

    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _placeholder() -> str:
    return "%s" if db_backend() == "postgres" else "?"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _execute(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> Any:
    return conn.execute(sql, params)


def _fetchone(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> Any:
    cur = _execute(conn, sql, params)
    return cur.fetchone()


def _create_sqlite_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS seen_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            normalized_url TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            title TEXT NOT NULL,
            source_name TEXT NOT NULL,
            first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            notified INTEGER NOT NULL DEFAULT 0,
            UNIQUE(normalized_url, content_hash)
        );

        CREATE TABLE IF NOT EXISTS agent_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            finished_at TEXT,
            status TEXT NOT NULL,
            sources_checked INTEGER NOT NULL DEFAULT 0,
            posts_found INTEGER NOT NULL DEFAULT 0,
            new_posts INTEGER NOT NULL DEFAULT 0,
            relevant_posts INTEGER NOT NULL DEFAULT 0,
            notifications_sent INTEGER NOT NULL DEFAULT 0,
            error_message TEXT
        );

        CREATE TABLE IF NOT EXISTS source_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            status TEXT NOT NULL,
            items_found INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            source_name TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            is_relevant INTEGER NOT NULL,
            relevance_score INTEGER NOT NULL DEFAULT 0,
            reason TEXT,
            notified INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS llm_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER,
            title TEXT NOT NULL,
            url TEXT,
            provider TEXT NOT NULL,
            model TEXT NOT NULL,
            status TEXT NOT NULL,
            response_json TEXT,
            parsed_json TEXT,
            error_message TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_seen_posts_url_hash ON seen_posts(normalized_url, content_hash)"
    )
    _dedupe_seen_posts_by_normalized_url(conn)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_seen_posts_normalized_url_unique ON seen_posts(normalized_url)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_seen_posts_content_hash ON seen_posts(content_hash)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_run_id ON findings(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_logs_run_id ON source_logs(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_logs_run_id ON llm_logs(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_llm_logs_created_at ON llm_logs(created_at)")
    _backfill_seen_posts_from_findings(conn)


def _create_postgres_schema(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_posts (
                id BIGSERIAL PRIMARY KEY,
                normalized_url TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                title TEXT NOT NULL,
                source_name TEXT NOT NULL,
                first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                notified BOOLEAN NOT NULL DEFAULT FALSE,
                UNIQUE(normalized_url, content_hash)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS agent_runs (
                id BIGSERIAL PRIMARY KEY,
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                finished_at TIMESTAMPTZ,
                status TEXT NOT NULL,
                sources_checked INTEGER NOT NULL DEFAULT 0,
                posts_found INTEGER NOT NULL DEFAULT 0,
                new_posts INTEGER NOT NULL DEFAULT 0,
                relevant_posts INTEGER NOT NULL DEFAULT 0,
                notifications_sent INTEGER NOT NULL DEFAULT 0,
                error_message TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS source_logs (
                id BIGSERIAL PRIMARY KEY,
                run_id BIGINT REFERENCES agent_runs(id) ON DELETE SET NULL,
                source_name TEXT NOT NULL,
                source_url TEXT NOT NULL,
                status TEXT NOT NULL,
                items_found INTEGER NOT NULL DEFAULT 0,
                error_message TEXT,
                checked_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS findings (
                id BIGSERIAL PRIMARY KEY,
                run_id BIGINT REFERENCES agent_runs(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source_name TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                is_relevant BOOLEAN NOT NULL,
                relevance_score INTEGER NOT NULL DEFAULT 0,
                reason TEXT,
                notified BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_logs (
                id BIGSERIAL PRIMARY KEY,
                run_id BIGINT REFERENCES agent_runs(id) ON DELETE SET NULL,
                title TEXT NOT NULL,
                url TEXT,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                status TEXT NOT NULL,
                response_json TEXT,
                parsed_json TEXT,
                error_message TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_seen_posts_url_hash ON seen_posts(normalized_url, content_hash)"
        )
        _dedupe_seen_posts_by_normalized_url(conn)
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_seen_posts_normalized_url_unique ON seen_posts(normalized_url)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_seen_posts_content_hash ON seen_posts(content_hash)"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_findings_run_id ON findings(run_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_source_logs_run_id ON source_logs(run_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_llm_logs_run_id ON llm_logs(run_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_llm_logs_created_at ON llm_logs(created_at)")
        _backfill_seen_posts_from_findings(conn)


def _sqlite_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cur.fetchone() is not None


def _sqlite_table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cur.fetchall()}


def _dedupe_seen_posts_by_normalized_url(conn: Any) -> None:
    if db_backend() == "postgres":
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM seen_posts
                WHERE id IN (
                    SELECT id
                    FROM (
                        SELECT id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY normalized_url
                                   ORDER BY first_seen_at ASC, id ASC
                               ) AS row_number
                        FROM seen_posts
                    ) duplicates
                    WHERE row_number > 1
                )
                """
            )
        return

    conn.execute(
        """
        DELETE FROM seen_posts
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM seen_posts
            GROUP BY normalized_url
        )
        """
    )


def _backfill_seen_posts_from_findings(conn: Any) -> None:
    ph = _placeholder()
    rows = _execute(
        conn,
        """
        SELECT title, url, source_name, content_hash, created_at, notified
        FROM findings
        ORDER BY created_at ASC, id ASC
        """,
    ).fetchall()

    if db_backend() == "postgres":
        with conn.cursor() as cur:
            for title, url, source_name, content_hash, created_at, notified in rows:
                cur.execute(
                    """
                    INSERT INTO seen_posts
                    (normalized_url, content_hash, title, source_name, first_seen_at, last_seen_at, notified)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (normalized_url) DO NOTHING
                    """,
                    (
                        normalize_url(url),
                        content_hash,
                        title,
                        source_name,
                        created_at or _now_iso(),
                        created_at or _now_iso(),
                        bool(notified),
                    ),
                )
        return

    for title, url, source_name, content_hash, created_at, notified in rows:
        _execute(
            conn,
            f"""
            INSERT OR IGNORE INTO seen_posts
            (normalized_url, content_hash, title, source_name, first_seen_at, last_seen_at, notified)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (
                normalize_url(url),
                content_hash,
                title,
                source_name,
                created_at or _now_iso(),
                created_at or _now_iso(),
                int(bool(notified)),
            ),
        )


def _migrate_legacy_sqlite(conn: sqlite3.Connection) -> None:
    if not _sqlite_table_exists(conn, LEGACY_TABLE_NAME):
        return

    columns = _sqlite_table_columns(conn, LEGACY_TABLE_NAME)
    content_hash_expr = "content_hash" if "content_hash" in columns else "NULL AS content_hash"
    cur = conn.execute(
        f"""
        SELECT source, title, url, snippet, {content_hash_expr}, first_seen_at, notified
        FROM {LEGACY_TABLE_NAME}
        """
    )
    rows = cur.fetchall()
    for source, title, url, snippet, content_hash, first_seen_at, notified in rows:
        hash_value = content_hash or compute_content_hash(title=title, snippet=snippet or "")
        conn.execute(
            """
            INSERT OR IGNORE INTO seen_posts
            (normalized_url, content_hash, title, source_name, first_seen_at, last_seen_at, notified)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                normalize_url(url),
                hash_value,
                title,
                source,
                first_seen_at or _now_iso(),
                first_seen_at or _now_iso(),
                int(bool(notified)),
            ),
        )


def init_db() -> None:
    with _connect() as conn:
        if db_backend() == "postgres":
            _create_postgres_schema(conn)
        else:
            _create_sqlite_schema(conn)
            _migrate_legacy_sqlite(conn)


def test_connection() -> str:
    init_db()
    with _connect() as conn:
        row = _fetchone(conn, f"SELECT 1")
    return f"{db_backend()} database connection OK: {row[0]}"


def start_agent_run(sources_checked: int = 0) -> int:
    with _connect() as conn:
        if db_backend() == "postgres":
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO agent_runs (status, sources_checked) VALUES (%s, %s) RETURNING id",
                    ("running", sources_checked),
                )
                return int(cur.fetchone()[0])

        cur = conn.execute(
            "INSERT INTO agent_runs (status, sources_checked) VALUES (?, ?)",
            ("running", sources_checked),
        )
        return int(cur.lastrowid)


def mark_stale_running_runs(sources_checked: int = 0) -> None:
    ph = _placeholder()
    with _connect() as conn:
        _execute(
            conn,
            f"""
            UPDATE agent_runs
            SET finished_at = {ph},
                status = {ph},
                sources_checked = CASE WHEN sources_checked = 0 THEN {ph} ELSE sources_checked END,
                error_message = COALESCE(error_message, {ph})
            WHERE status = {ph}
            """,
            (
                _now_iso(),
                "failed",
                sources_checked,
                "Run did not finish before the next scanner start.",
                "running",
            ),
        )


def finish_agent_run(
    run_id: int,
    status: str,
    sources_checked: int,
    posts_found: int,
    new_posts: int,
    relevant_posts: int,
    notifications_sent: int,
    error_message: str = "",
) -> None:
    ph = _placeholder()
    with _connect() as conn:
        _execute(
            conn,
            f"""
            UPDATE agent_runs
            SET finished_at = {ph},
                status = {ph},
                sources_checked = {ph},
                posts_found = {ph},
                new_posts = {ph},
                relevant_posts = {ph},
                notifications_sent = {ph},
                error_message = {ph}
            WHERE id = {ph}
            """,
            (
                _now_iso(),
                status,
                sources_checked,
                posts_found,
                new_posts,
                relevant_posts,
                notifications_sent,
                error_message or None,
                run_id,
            ),
        )


def log_source_check(
    run_id: int | None,
    source_name: str,
    source_url: str,
    status: str,
    items_found: int = 0,
    error_message: str = "",
) -> None:
    ph = _placeholder()
    with _connect() as conn:
        _execute(
            conn,
            f"""
            INSERT INTO source_logs
            (run_id, source_name, source_url, status, items_found, error_message, checked_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (
                run_id,
                source_name,
                source_url,
                status,
                items_found,
                error_message or None,
                _now_iso(),
            ),
        )


def seen_post_diagnostics(url: str, content_hash: str) -> dict[str, Any]:
    normalized_url = normalize_url(url)
    ph = _placeholder()
    with _connect() as conn:
        url_row = _fetchone(
            conn,
            f"SELECT 1 FROM seen_posts WHERE normalized_url = {ph}",
            (normalized_url,),
        )
        hash_row = _fetchone(
            conn,
            f"SELECT 1 FROM seen_posts WHERE content_hash = {ph}",
            (content_hash,),
        )
        already_seen_by_url = url_row is not None
        already_seen_by_hash = hash_row is not None
        if not already_seen_by_url and not already_seen_by_hash:
            return {
                "normalized_url": normalized_url,
                "already_seen_by_url": False,
                "already_seen_by_hash": False,
                "already_seen": False,
            }

        _execute(
            conn,
            f"""
            UPDATE seen_posts
            SET last_seen_at = {ph}
            WHERE normalized_url = {ph} OR content_hash = {ph}
            """,
            (_now_iso(), normalized_url, content_hash),
        )
        return {
            "normalized_url": normalized_url,
            "already_seen_by_url": already_seen_by_url,
            "already_seen_by_hash": already_seen_by_hash,
            "already_seen": True,
        }


def already_seen(url: str, content_hash: str) -> bool:
    return bool(seen_post_diagnostics(url, content_hash)["already_seen"])


def save_seen_post(
    source_name: str,
    title: str,
    url: str,
    content_hash: str,
    notified: bool = False,
) -> bool:
    normalized_url = normalize_url(url)
    ph = _placeholder()
    with _connect() as conn:
        if db_backend() == "postgres":
            with conn.cursor() as cur:
                cur.execute(
                    """
                INSERT INTO seen_posts
                (normalized_url, content_hash, title, source_name, first_seen_at, last_seen_at, notified)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (normalized_url)
                DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at,
                              content_hash = EXCLUDED.content_hash,
                              title = EXCLUDED.title,
                              source_name = EXCLUDED.source_name,
                              notified = seen_posts.notified OR EXCLUDED.notified
                RETURNING (xmax = 0) AS inserted
                """,
                    (normalized_url, content_hash, title, source_name, _now_iso(), _now_iso(), notified),
                )
                return bool(cur.fetchone()[0])

        cur = _execute(
            conn,
            f"""
            INSERT OR IGNORE INTO seen_posts
            (normalized_url, content_hash, title, source_name, first_seen_at, last_seen_at, notified)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (
                normalized_url,
                content_hash,
                title,
                source_name,
                _now_iso(),
                _now_iso(),
                int(notified),
            ),
        )
        inserted = cur.rowcount > 0
        if not inserted:
            _execute(
                conn,
                f"""
                UPDATE seen_posts
                SET last_seen_at = {ph},
                    content_hash = {ph},
                    title = {ph},
                    source_name = {ph},
                    notified = notified OR {ph}
                WHERE normalized_url = {ph}
                """,
                (_now_iso(), content_hash, title, source_name, int(notified), normalized_url),
            )
        return inserted


def save_finding(
    run_id: int | None,
    title: str,
    url: str,
    source_name: str,
    content_hash: str,
    is_relevant: bool,
    relevance_score: int,
    reason: str = "",
    notified: bool = False,
) -> None:
    ph = _placeholder()
    with _connect() as conn:
        _execute(
            conn,
            f"""
            INSERT INTO findings
            (run_id, title, url, source_name, content_hash, is_relevant, relevance_score, reason, notified, created_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (
                run_id,
                title,
                url,
                source_name,
                content_hash,
                is_relevant if db_backend() == "postgres" else int(is_relevant),
                relevance_score,
                reason or None,
                notified if db_backend() == "postgres" else int(notified),
                _now_iso(),
            ),
        )


def log_llm_response(
    run_id: int | None,
    title: str,
    url: str = "",
    provider: str = "gemini",
    model: str = "",
    status: str = "success",
    response_json: Any | None = None,
    parsed_json: Any | None = None,
    error_message: str = "",
) -> None:
    ph = _placeholder()
    response_text = (
        json.dumps(response_json, ensure_ascii=False)
        if response_json is not None
        else None
    )
    parsed_text = (
        json.dumps(parsed_json, ensure_ascii=False)
        if parsed_json is not None
        else None
    )

    with _connect() as conn:
        _execute(
            conn,
            f"""
            INSERT INTO llm_logs
            (run_id, title, url, provider, model, status, response_json, parsed_json, error_message, created_at)
            VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            """,
            (
                run_id,
                title,
                url or None,
                provider,
                model,
                status,
                response_text,
                parsed_text,
                error_message or None,
                _now_iso(),
            ),
        )


def save_opportunity(
    source: str,
    title: str,
    url: str,
    snippet: str,
    content_hash: str,
    score: int,
) -> None:
    save_seen_post(source_name=source, title=title, url=url, content_hash=content_hash)


def mark_notified(url: str, content_hash: str) -> None:
    normalized_url = normalize_url(url)
    ph = _placeholder()
    with _connect() as conn:
        _execute(
            conn,
            f"""
            UPDATE seen_posts
            SET notified = {ph}, last_seen_at = {ph}
            WHERE normalized_url = {ph} AND content_hash = {ph}
            """,
            (
                True if db_backend() == "postgres" else 1,
                _now_iso(),
                normalized_url,
                content_hash,
            ),
        )
