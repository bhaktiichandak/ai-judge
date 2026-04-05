import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.llm import SourceRecord
from backend.main import app


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    @patch("backend.routes.save_chat_session", return_value=False)
    def test_chat_returns_deterministic_reply_without_external_models(self, mocked_save_chat_session):
        response = self.client.post(
            "/api/chat",
            json={
                "message": "Review this Python function for bugs: def add(a, b):\n    return a + b",
                "history": [],
                "model": "deterministic-consensus",
                "mode": "judge",
                "session_id": "session-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["model_used"], "deterministic-consensus")
        self.assertEqual(payload["task_kind"], "code")
        self.assertIn("## Final Consensus Verdict", payload["reply"])
        self.assertIn("## Risks", payload["reply"])
        self.assertEqual(payload["sources"], [])
        self.assertIsNone(payload["error"])
        self.assertEqual(payload["session_id"], "session-123")
        self.assertEqual(payload["storage_backend"], "local")
        mocked_save_chat_session.assert_called_once()

    @patch("backend.llm.collect_sources")
    @patch("backend.routes.save_chat_session", return_value=True)
    def test_credibility_response_serializes_backend_sources(self, mocked_save_chat_session, mocked_collect_sources):
        mocked_collect_sources.return_value = (
            ["Python was created by Guido van Rossum"],
            [
                SourceRecord(
                    claim="Python was created by Guido van Rossum",
                    title="Python FAQ",
                    url="https://docs.python.org/3/faq/general.html",
                    snippet="Python was created by Guido van Rossum in the late 1980s.",
                    published="Date unavailable",
                    source_type="Official technical documentation",
                    credibility_tier="High",
                    score=4,
                    relevance=5,
                )
            ],
        )

        response = self.client.post(
            "/api/chat",
            json={
                "message": "Who created Python? Please give sources.",
                "history": [],
                "model": "deterministic-consensus",
                "mode": "credibility",
                "session_id": "credibility-session",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload["sources"]), 1)
        self.assertEqual(payload["sources"][0]["url"], "https://docs.python.org/3/faq/general.html")
        self.assertIn("Python FAQ", payload["reply"])
        self.assertIn("## Sources & References", payload["reply"])
        self.assertEqual(payload["storage_backend"], "mongo")
        mocked_save_chat_session.assert_called_once()

    @patch("backend.routes.load_chat_session")
    def test_session_endpoint_returns_messages(self, mocked_load_chat_session):
        mocked_load_chat_session.return_value = [
            {
                "role": "user",
                "content": "hello",
                "hidden": False,
                "sources": [],
            },
            {
                "role": "assistant",
                "content": "hi there",
                "hidden": False,
                "sources": [{"title": "Example", "url": "https://example.com"}],
            },
        ]

        response = self.client.get("/api/sessions/chat-42")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["session_id"], "chat-42")
        self.assertEqual(len(payload["messages"]), 2)
        self.assertEqual(payload["messages"][1]["content"], "hi there")


if __name__ == "__main__":
    unittest.main()
