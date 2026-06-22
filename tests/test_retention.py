import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src import main


class RetentionTests(unittest.TestCase):
    def test_cleanup_failure_does_not_escape(self):
        settings = SimpleNamespace(data_retention_days=90)
        with (
            patch.object(main, "settings", settings),
            patch.object(
                main,
                "cleanup_expired_data",
                side_effect=RuntimeError("database unavailable"),
            ),
        ):
            main.cleanup_expired_history()

    def test_zero_retention_disables_cleanup(self):
        settings = SimpleNamespace(data_retention_days=0)
        with (
            patch.object(main, "settings", settings),
            patch.object(main, "cleanup_expired_data") as cleanup,
        ):
            main.cleanup_expired_history()

        cleanup.assert_not_called()


if __name__ == "__main__":
    unittest.main()
