import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src import db


def sqlite_settings(path: Path, touch_interval_hours: int = 24):
    return SimpleNamespace(
        db_backend="sqlite",
        database_url="",
        sqlite_path=str(path),
        seen_post_touch_interval_hours=touch_interval_hours,
    )


class DedupTests(unittest.TestCase):
    def test_same_url_is_seen_even_if_content_hash_changes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "ra.sqlite"
            with patch.object(db, "settings", sqlite_settings(sqlite_path)):
                db.init_db()
                first_hash = db.compute_content_hash("Title", "Description one")
                second_hash = db.compute_content_hash("Title", "Description two")

                inserted = db.save_seen_post(
                    source_name="source",
                    title="Title",
                    url="https://example.edu/post/1?b=2&a=1",
                    content_hash=first_hash,
                )
                diagnostics = db.seen_post_diagnostics(
                    "https://EXAMPLE.edu/post/1?a=1&b=2",
                    second_hash,
                )

            self.assertTrue(inserted)
            self.assertTrue(diagnostics["already_seen"])
            self.assertTrue(diagnostics["already_seen_by_url"])
            self.assertFalse(diagnostics["already_seen_by_hash"])

    def test_content_hash_ignores_dynamic_status_metadata(self):
        first_hash = db.compute_content_hash(
            "Research Assistant",
            "Core description | Status: OPEN | Researcher: Prof. Chen",
        )
        second_hash = db.compute_content_hash(
            "Research Assistant",
            "Core description | Status: CLOSED | Researcher: Prof. Chen",
        )

        self.assertEqual(first_hash, second_hash)

    def test_init_db_backfills_seen_posts_from_findings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "ra.sqlite"
            with patch.object(db, "settings", sqlite_settings(sqlite_path)):
                db.init_db()
                content_hash = db.compute_content_hash("Existing finding", "Stable description")
                db.save_finding(
                    run_id=None,
                    title="Existing finding",
                    url="https://example.edu/post/old",
                    source_name="source",
                    content_hash=content_hash,
                    is_relevant=True,
                    relevance_score=3,
                    reason="historical",
                    notified=True,
                )

                db.init_db()
                diagnostics = db.seen_post_diagnostics(
                    "https://example.edu/post/old",
                    content_hash,
                )

            self.assertTrue(diagnostics["already_seen"])
            self.assertTrue(diagnostics["already_seen_by_url"])
            self.assertTrue(diagnostics["already_seen_by_hash"])

    def test_seen_post_touch_is_throttled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "ra.sqlite"
            with patch.object(db, "settings", sqlite_settings(sqlite_path)):
                db.init_db()
                content_hash = db.compute_content_hash("Title", "Description")
                db.save_seen_post(
                    source_name="source",
                    title="Title",
                    url="https://example.edu/post/1",
                    content_hash=content_hash,
                )
                with closing(sqlite3.connect(sqlite_path)) as conn:
                    before = conn.execute(
                        "SELECT last_seen_at FROM seen_posts"
                    ).fetchone()[0]

                db.seen_post_diagnostics(
                    "https://example.edu/post/1", content_hash
                )

                with closing(sqlite3.connect(sqlite_path)) as conn:
                    after = conn.execute(
                        "SELECT last_seen_at FROM seen_posts"
                    ).fetchone()[0]

            self.assertEqual(after, before)

    def test_seen_post_touch_updates_after_interval(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "ra.sqlite"
            with patch.object(db, "settings", sqlite_settings(sqlite_path)):
                db.init_db()
                content_hash = db.compute_content_hash("Title", "Description")
                db.save_seen_post(
                    source_name="source",
                    title="Title",
                    url="https://example.edu/post/1",
                    content_hash=content_hash,
                )
                old_timestamp = (
                    datetime.now(timezone.utc) - timedelta(hours=25)
                ).isoformat()
                with closing(sqlite3.connect(sqlite_path)) as conn:
                    conn.execute(
                        "UPDATE seen_posts SET last_seen_at = ?",
                        (old_timestamp,),
                    )
                    conn.commit()

                db.seen_post_diagnostics(
                    "https://example.edu/post/1", content_hash
                )

                with closing(sqlite3.connect(sqlite_path)) as conn:
                    after = conn.execute(
                        "SELECT last_seen_at FROM seen_posts"
                    ).fetchone()[0]

            self.assertGreater(
                datetime.fromisoformat(after), datetime.fromisoformat(old_timestamp)
            )

    def test_zero_touch_interval_updates_every_sighting(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "ra.sqlite"
            with patch.object(db, "settings", sqlite_settings(sqlite_path, 0)):
                db.init_db()
                content_hash = db.compute_content_hash("Title", "Description")
                db.save_seen_post(
                    source_name="source",
                    title="Title",
                    url="https://example.edu/post/1",
                    content_hash=content_hash,
                )
                old_timestamp = (
                    datetime.now(timezone.utc) - timedelta(minutes=1)
                ).isoformat()
                with closing(sqlite3.connect(sqlite_path)) as conn:
                    conn.execute(
                        "UPDATE seen_posts SET last_seen_at = ?",
                        (old_timestamp,),
                    )
                    conn.commit()

                db.seen_post_diagnostics(
                    "https://example.edu/post/1", content_hash
                )

                with closing(sqlite3.connect(sqlite_path)) as conn:
                    after = conn.execute(
                        "SELECT last_seen_at FROM seen_posts"
                    ).fetchone()[0]

            self.assertGreater(
                datetime.fromisoformat(after), datetime.fromisoformat(old_timestamp)
            )

    def test_cleanup_removes_expired_history_but_keeps_seen_posts(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "ra.sqlite"
            with patch.object(db, "settings", sqlite_settings(sqlite_path)):
                db.init_db()
                content_hash = db.compute_content_hash("Title", "Description")
                db.save_seen_post(
                    source_name="source",
                    title="Title",
                    url="https://example.edu/post/1",
                    content_hash=content_hash,
                )
                old_run_id = db.start_agent_run(1)
                db.log_source_check(
                    old_run_id,
                    "source",
                    "https://example.edu",
                    "success",
                    1,
                )
                db.save_finding(
                    old_run_id,
                    "Title",
                    "https://example.edu/post/1",
                    "source",
                    content_hash,
                    True,
                    3,
                )
                db.log_llm_response(
                    run_id=old_run_id,
                    title="Title",
                    url="https://example.edu/post/1",
                    model="test-model",
                )
                old_timestamp = (
                    datetime.now(timezone.utc) - timedelta(days=91)
                ).isoformat()
                with closing(sqlite3.connect(sqlite_path)) as conn:
                    conn.execute(
                        "UPDATE agent_runs SET started_at = ? WHERE id = ?",
                        (old_timestamp, old_run_id),
                    )
                    conn.commit()

                deleted = db.cleanup_expired_data(
                    datetime.now(timezone.utc) - timedelta(days=90)
                )

                with closing(sqlite3.connect(sqlite_path)) as conn:
                    counts = {
                        table: conn.execute(
                            f"SELECT COUNT(*) FROM {table}"
                        ).fetchone()[0]
                        for table in (
                            "seen_posts",
                            "agent_runs",
                            "source_logs",
                            "findings",
                            "llm_logs",
                        )
                    }

            self.assertEqual(deleted["agent_runs"], 1)
            self.assertEqual(deleted["source_logs"], 1)
            self.assertEqual(deleted["findings"], 1)
            self.assertEqual(deleted["llm_logs"], 1)
            self.assertEqual(counts["seen_posts"], 1)
            self.assertEqual(counts["agent_runs"], 0)
            self.assertEqual(counts["source_logs"], 0)
            self.assertEqual(counts["findings"], 0)
            self.assertEqual(counts["llm_logs"], 0)

    def test_cleanup_keeps_recent_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "ra.sqlite"
            with patch.object(db, "settings", sqlite_settings(sqlite_path)):
                db.init_db()
                run_id = db.start_agent_run(1)
                db.log_source_check(
                    run_id,
                    "source",
                    "https://example.edu",
                    "success",
                    1,
                )

                deleted = db.cleanup_expired_data(
                    datetime.now(timezone.utc) - timedelta(days=90)
                )

            self.assertEqual(deleted["agent_runs"], 0)
            self.assertEqual(deleted["source_logs"], 0)


if __name__ == "__main__":
    unittest.main()
