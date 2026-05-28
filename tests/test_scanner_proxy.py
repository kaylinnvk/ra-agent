import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src import scanner


class MockSession:
    def __init__(self):
        self.trust_env = True
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return "response"


class MockJsonResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class ScannerProxyTests(unittest.TestCase):
    def test_website_fetch_ignores_environment_proxy_when_disabled(self):
        system_session = MockSession()
        no_proxy_session = MockSession()
        no_proxy_session.trust_env = True

        with (
            patch.object(scanner, "settings", SimpleNamespace(use_system_proxy=False)),
            patch.object(scanner, "_SYSTEM_PROXY_SESSION", system_session),
            patch.object(scanner, "_NO_PROXY_SESSION", no_proxy_session),
        ):
            response = scanner._get("https://example.edu/ra", timeout=20)

        self.assertEqual(response, "response")
        self.assertFalse(no_proxy_session.trust_env)
        self.assertEqual(no_proxy_session.calls, [("https://example.edu/ra", {"timeout": 20})])
        self.assertEqual(system_session.calls, [])

    def test_website_fetch_keeps_system_proxy_behavior_when_enabled(self):
        system_session = MockSession()
        no_proxy_session = MockSession()
        no_proxy_session.trust_env = False

        with (
            patch.object(scanner, "settings", SimpleNamespace(use_system_proxy=True)),
            patch.object(scanner, "_SYSTEM_PROXY_SESSION", system_session),
            patch.object(scanner, "_NO_PROXY_SESSION", no_proxy_session),
        ):
            response = scanner._get("https://example.edu/ra", timeout=20)

        self.assertEqual(response, "response")
        self.assertTrue(system_session.trust_env)
        self.assertEqual(system_session.calls, [("https://example.edu/ra", {"timeout": 20})])
        self.assertEqual(no_proxy_session.calls, [])

    def test_api_post_fetch_requests_json(self):
        calls = []

        def fake_get(url, **kwargs):
            calls.append((url, kwargs))
            return MockJsonResponse(
                {
                    "count": 1,
                    "next": None,
                    "results": [
                        {
                            "id": "post-1",
                            "title": "Research Assistant Opening - AI Agents",
                            "description": "Work on agentic AI systems.",
                            "requirements": "Python and ML.",
                            "researcher_name": "Prof. Chen",
                            "school": "SDS",
                            "status": "OPEN",
                            "deadline": "2026-06-30",
                            "tags": [{"name": "LLM"}, {"name": "AI Agents"}],
                        }
                    ],
                }
            )

        with patch.object(scanner, "_get", side_effect=fake_get):
            items = scanner._extract_api_posts("https://www.ssccuhksz.club/search")

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Research Assistant Opening - AI Agents")
        self.assertEqual(items[0].url, "https://www.ssccuhksz.club/post/post-1")
        self.assertIn("Prof. Chen", items[0].snippet)
        self.assertEqual(calls[0][1]["headers"]["Accept"], "application/json")


if __name__ == "__main__":
    unittest.main()
