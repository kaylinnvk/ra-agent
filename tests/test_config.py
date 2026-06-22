import os
import unittest
from unittest.mock import patch

from src.config import Settings


class ConfigTests(unittest.TestCase):
    def test_blank_gemini_base_url_uses_default(self):
        with patch.dict(os.environ, {"GEMINI_BASE_URL": "   "}, clear=True):
            settings = Settings()

        self.assertEqual(
            settings.gemini_base_url,
            "https://generativelanguage.googleapis.com/v1beta",
        )

    def test_blank_gemini_model_uses_default(self):
        with patch.dict(os.environ, {"GEMINI_MODEL": ""}, clear=True):
            settings = Settings()

        self.assertEqual(settings.gemini_model, "gemini-2.0-flash")

    def test_retention_defaults(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

        self.assertEqual(settings.data_retention_days, 90)
        self.assertEqual(settings.seen_post_touch_interval_hours, 24)

    def test_retention_can_be_disabled(self):
        with patch.dict(
            os.environ,
            {
                "DATA_RETENTION_DAYS": "0",
                "SEEN_POST_TOUCH_INTERVAL_HOURS": "0",
            },
            clear=True,
        ):
            settings = Settings()

        self.assertEqual(settings.data_retention_days, 0)
        self.assertEqual(settings.seen_post_touch_interval_hours, 0)


if __name__ == "__main__":
    unittest.main()
