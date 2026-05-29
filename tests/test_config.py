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


if __name__ == "__main__":
    unittest.main()
