import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src import db


def sqlite_settings(path: Path):
    return SimpleNamespace(
        db_backend="sqlite",
        database_url="",
        sqlite_path=str(path),
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


if __name__ == "__main__":
    unittest.main()
