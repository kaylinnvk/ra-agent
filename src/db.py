import hashlib
import sqlite3
from pathlib import Path

DB_PATH = Path("ra_agent.db")
TABLE_NAME = "opportunities"


def compute_content_hash(title: str, snippet: str = "") -> str:
    normalized_title = " ".join((title or "").split()).strip().lower()
    normalized_snippet = " ".join((snippet or "").split()).strip().lower()
    payload = f"{normalized_title}\n{normalized_snippet}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cur = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cur.fetchone() is not None


def _table_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cur = conn.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cur.fetchall()}


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            snippet TEXT,
            content_hash TEXT NOT NULL,
            score INTEGER NOT NULL,
            first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notified INTEGER DEFAULT 0,
            UNIQUE(url, content_hash)
        )
        """
    )


def _migrate_if_needed(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, TABLE_NAME):
        _create_schema(conn)
        return

    columns = _table_columns(conn, TABLE_NAME)
    if "content_hash" in columns:
        return

    legacy_table = f"{TABLE_NAME}_legacy"
    conn.execute(f"ALTER TABLE {TABLE_NAME} RENAME TO {legacy_table}")
    _create_schema(conn)

    cur = conn.execute(
        f"""
        SELECT source, title, url, snippet, score, first_seen_at, notified
        FROM {legacy_table}
        """
    )
    rows = cur.fetchall()

    for source, title, url, snippet, score, first_seen_at, notified in rows:
        content_hash = compute_content_hash(title=title, snippet=snippet or "")
        conn.execute(
            f"""
            INSERT OR IGNORE INTO {TABLE_NAME}
            (source, title, url, snippet, content_hash, score, first_seen_at, notified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source, title, url, snippet, content_hash, score, first_seen_at, notified),
        )

    conn.execute(f"DROP TABLE {legacy_table}")

def init_db() -> None:
    with sqlite3.connect(DB_PATH) as conn:
        _migrate_if_needed(conn)
        _create_schema(conn)

def already_seen(url: str, content_hash: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            f"SELECT 1 FROM {TABLE_NAME} WHERE url = ? AND content_hash = ?",
            (url, content_hash),
        )
        return cur.fetchone() is not None

def save_opportunity(
    source: str,
    title: str,
    url: str,
    snippet: str,
    content_hash: str,
    score: int,
) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"""
            INSERT OR IGNORE INTO {TABLE_NAME}
            (source, title, url, snippet, content_hash, score)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (source, title, url, snippet, content_hash, score),
        )

def mark_notified(url: str, content_hash: str) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            f"UPDATE {TABLE_NAME} SET notified = 1 WHERE url = ? AND content_hash = ?",
            (url, content_hash),
        )
