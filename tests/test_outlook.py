import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src import outlook


class MockResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def outlook_settings(**overrides):
    values = {
        "use_outlook_source": True,
        "microsoft_tenant_id": "tenant-id",
        "microsoft_client_id": "client-id",
        "microsoft_client_secret": "client-secret",
        "microsoft_token_url": "https://login.microsoftonline.com/tenant-id/oauth2/v2.0/token",
        "outlook_mailbox": "student@example.edu",
        "outlook_folder": "inbox",
        "outlook_max_messages": 10,
        "outlook_search_query": "",
        "graph_base_url": "https://graph.microsoft.com/v1.0",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class OutlookSourceTests(unittest.TestCase):
    def test_fetches_and_formats_outlook_messages(self):
        message = {
            "id": "message-1",
            "subject": "Research Assistant Opening - AI Agents Lab",
            "from": {
                "emailAddress": {
                    "name": "Prof. Maya Chen",
                    "address": "maya.chen@example.edu",
                }
            },
            "receivedDateTime": "2026-05-27T10:30:00Z",
            "bodyPreview": "We are hiring an RA to work on LLM agents.",
            "body": {
                "contentType": "text",
                "content": "We are hiring an RA to work on LLM agents. Deadline: June 30.",
            },
            "webLink": "https://outlook.office.com/mail/id/message-1",
        }

        with (
            patch.object(outlook, "settings", outlook_settings()),
            patch.object(outlook.requests, "post") as post,
            patch.object(outlook.requests, "get") as get,
        ):
            post.return_value = MockResponse({"access_token": "token-123"})
            get.return_value = MockResponse({"value": [message]})

            items = outlook.fetch_outlook_messages()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].title, "Research Assistant Opening - AI Agents Lab")
        self.assertEqual(items[0].url, "https://outlook.office.com/mail/id/message-1")
        self.assertIn("Prof. Maya Chen <maya.chen@example.edu>", items[0].snippet)
        self.assertIn("Deadline: June 30.", items[0].snippet)

        post.assert_called_once()
        self.assertEqual(post.call_args.kwargs["data"]["grant_type"], "client_credentials")
        self.assertEqual(post.call_args.kwargs["data"]["scope"], outlook.GRAPH_SCOPE)

        get.assert_called_once()
        self.assertEqual(
            get.call_args.args[0],
            "https://graph.microsoft.com/v1.0/users/student%40example.edu/mailFolders/inbox/messages",
        )
        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer token-123")
        self.assertEqual(get.call_args.kwargs["params"]["$top"], 10)

    def test_adds_search_query_when_configured(self):
        with (
            patch.object(outlook, "settings", outlook_settings(outlook_search_query='RA "LLM"')),
            patch.object(outlook.requests, "post") as post,
            patch.object(outlook.requests, "get") as get,
        ):
            post.return_value = MockResponse({"access_token": "token-123"})
            get.return_value = MockResponse({"value": []})

            outlook.fetch_outlook_messages()

        self.assertEqual(get.call_args.kwargs["params"]["$search"], '"RA LLM"')
        self.assertNotIn("$orderby", get.call_args.kwargs["params"])

    def test_has_outlook_config_requires_enabled_credentials_and_mailbox(self):
        with patch.object(outlook, "settings", outlook_settings()):
            self.assertTrue(outlook.has_outlook_config())

        with patch.object(outlook, "settings", outlook_settings(use_outlook_source=False)):
            self.assertFalse(outlook.has_outlook_config())

        with patch.object(outlook, "settings", outlook_settings(microsoft_client_secret="")):
            self.assertFalse(outlook.has_outlook_config())


if __name__ == "__main__":
    unittest.main()
