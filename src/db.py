import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from src.config import settings

LEGACY_TABLE_NAME = "opportunities"


def compute_content_hash(title: str, snippet: str = "") -> str:
    normalized_title = " ".join((title or "").split()).strip().lower()
    normalized_snippet = " ".join((snippet or "").split()).strip().lower()
    payload = f"{normalized_title}\n{normalized_snippet}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
    with sqlite3.connect(path) as conn:
        yield conn


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
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_seen_posts_url_hash ON seen_posts(normalized_url, content_hash)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_findings_run_id ON findings(run_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_source_logs_run_id ON source_logs(run_id)")


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
            "CREATE INDEX IF NOT EXISTS idx_seen_posts_url_hash ON seen_posts(normalized_url, content_hash)"
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_findings_run_id ON findings(run_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_source_logs_run_id ON source_logs(run_id)")


def _sqlite_table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cur.fetchone() is not None


def _sqlite_table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cur.fetchall()}


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


def start_agent_run() -> int:
    with _connect() as conn:
        if db_backend() == "postgres":
            with conn.cursor() as cur:
                cur.execute("INSERT INTO agent_runs (status) VALUES (%s) RETURNING id", ("running",))
                return int(cur.fetchone()[0])

        cur = conn.execute("INSERT INTO agent_runs (status) VALUES (?)", ("running",))
        return int(cur.lastrowid)


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


def already_seen(url: str, content_hash: str) -> bool:
    normalized_url = normalize_url(url)
    ph = _placeholder()
    with _connect() as conn:
        row = _fetchone(
            conn,
            f"SELECT 1 FROM seen_posts WHERE normalized_url = {ph} AND content_hash = {ph}",
            (normalized_url, content_hash),
        )
        if row is None:
            return False
        _execute(
            conn,
            f"""
            UPDATE seen_posts
            SET last_seen_at = {ph}
            WHERE normalized_url = {ph} AND content_hash = {ph}
            """,
            (_now_iso(), normalized_url, content_hash),
        )
        return True


def save_seen_post(
    source_name: str,
    title: str,
    url: str,
    content_hash: str,
    notified: bool = False,
) -> None:
    normalized_url = normalize_url(url)
    ph = _placeholder()
    with _connect() as conn:
        if db_backend() == "postgres":
            _execute(
                conn,
                """
                INSERT INTO seen_posts
                (normalized_url, content_hash, title, source_name, first_seen_at, last_seen_at, notified)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (normalized_url, content_hash)
                DO UPDATE SET last_seen_at = EXCLUDED.last_seen_at
                """,
                (normalized_url, content_hash, title, source_name, _now_iso(), _now_iso(), notified),
            )
            return

        _execute(
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
