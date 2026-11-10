"""Tests for the HTTP API: health, settings, conversations and the SSE stream."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.config import Settings
from app.llm.client import ToolCall
from app.main import app
from app.schemas.conversation import Conversation, Message
from app.services.conversation_store import InMemoryConversationStore
from tests.conftest import FakeLLM, FakeSearchProvider, make_results


@pytest.fixture
def client(settings: Settings):
    """A TestClient wired to fake providers (no network access)."""
    provider = FakeSearchProvider(make_results(2))
    llm = FakeLLM(
        [
            [ToolCall(id="1", name="web_search", args={"query": "test query"})],
            "Here is the researched answer.",
        ]
    )
    from app.agent.controller import AgentController

    controller = AgentController(
        settings=settings,
        llm=llm,
        search_provider=provider,
        store=InMemoryConversationStore(),
    )
    deps.get_controller.cache_clear()
    deps.get_store.cache_clear()
    app.dependency_overrides[deps.get_controller] = lambda: controller
    app.dependency_overrides[deps.get_store] = lambda: controller.store
    app.dependency_overrides[deps.get_app_settings] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def parse_sse(payload: str) -> list[tuple[str, dict]]:
    """Parse an SSE body into ``(event_name, data)`` tuples."""
    events: list[tuple[str, dict]] = []
    name = ""
    data_lines: list[str] = []
    for line in payload.splitlines():
        if line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            data_lines.append(line[5:].strip())
        elif line == "" and data_lines:
            try:
                events.append((name, json.loads("\n".join(data_lines))))
            except json.JSONDecodeError:
                pass
            data_lines = []
            name = ""
    return events


class TestHealth:
    def test_health_endpoint(self, client) -> None:
        response = client.get("/api/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["version"]

    def test_root_endpoint(self, client) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["docs"] == "/api/docs"


class TestSettingsRedaction:
    def test_settings_never_leak_secrets(self, client) -> None:
        response = client.get("/api/settings")
        assert response.status_code == 200
        body = response.json()
        raw = response.text
        assert "test-key" not in raw
        assert "api_key" not in raw.lower()
        assert body["feature_flags"]["gemini_configured"] is True
        assert body["model"] == "gemini-2.5-flash"


class TestConversations:
    def test_create_list_and_delete(self, client) -> None:
        created = client.post("/api/conversations", json={"title": "Demo"})
        assert created.status_code == 201
        conversation_id = created.json()["id"]

        listing = client.get("/api/conversations").json()
        assert any(item["id"] == conversation_id for item in listing)

        renamed = client.patch(
            f"/api/conversations/{conversation_id}", json={"title": "Renamed"}
        )
        assert renamed.json()["title"] == "Renamed"

        assert client.delete(f"/api/conversations/{conversation_id}").status_code == 200
        assert client.get(f"/api/conversations/{conversation_id}").status_code == 404

    def test_rename_rejects_blank_title(self, client) -> None:
        created = client.post("/api/conversations", json={}).json()
        response = client.patch(
            f"/api/conversations/{created['id']}", json={"title": "  "}
        )
        assert response.status_code == 422

    def test_saved_searches_crud(self, client) -> None:
        created = client.post("/api/saved-searches", json={"query": "renewable energy"})
        assert created.status_code == 201
        search_id = created.json()["id"]
        assert any(s["id"] == search_id for s in client.get("/api/saved-searches").json())
        assert client.delete(f"/api/saved-searches/{search_id}").status_code == 200


class TestChatStream:
    def test_stream_emits_the_full_event_sequence(self, client) -> None:
        response = client.post(
            "/api/chat/stream",
            json={"message": "Tell me about Nexus", "run_id": "run-1"},
        )
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        events = parse_sse(response.text)
        names = [name for name, _ in events]

        assert names[0] == "agent_started"
        assert "planning" in names
        assert "tool_selected" in names
        assert "tool_call" in names
        assert "tool_started" in names
        assert "tool_result" in names
        assert "observation" in names
        assert "final_answer" in names
        assert names[-2] == "agent_completed"
        assert names[-1] == "done"

    def test_tool_result_event_carries_real_results(self, client) -> None:
        response = client.post(
            "/api/chat/stream", json={"message": "Research something", "run_id": "run-2"}
        )
        events = parse_sse(response.text)
        tool_result = next(data for name, data in events if name == "tool_result")
        payload = tool_result["data"]
        assert payload["ok"] is True
        assert payload["result_count"] == 2
        assert payload["results"][0]["url"].startswith("https://example.com/")

    def test_final_answer_is_returned(self, client) -> None:
        response = client.post(
            "/api/chat/stream", json={"message": "Research something", "run_id": "run-3"}
        )
        events = parse_sse(response.text)
        final = next(data for name, data in events if name == "final_answer")
        assert "researched answer" in final["data"]["content"]

    def test_completed_event_reports_statistics(self, client) -> None:
        response = client.post(
            "/api/chat/stream", json={"message": "Research something", "run_id": "run-4"}
        )
        events = parse_sse(response.text)
        completed = next(data for name, data in events if name == "agent_completed")
        assert completed["data"]["tool_calls"] == 1
        assert completed["data"]["iterations"] >= 2
        assert completed["data"]["source_count"] == 2

    def test_blank_message_is_rejected(self, client) -> None:
        response = client.post("/api/chat/stream", json={"message": "   "})
        assert response.status_code == 422

    def test_stop_endpoint_reports_unknown_run(self, client) -> None:
        response = client.post("/api/chat/stop", json={"run_id": "does-not-exist"})
        assert response.status_code == 200
        assert response.json()["stopped"] is False


class TestConversationPersistence:
    def test_stream_creates_and_updates_a_conversation(self, client) -> None:
        response = client.post(
            "/api/chat/stream", json={"message": "Remember this research", "run_id": "run-5"}
        )
        events = parse_sse(response.text)
        started = next(data for name, data in events if name == "agent_started")
        conversation_id = started["data"]["conversation_id"]

        conversation = client.get(f"/api/conversations/{conversation_id}").json()
        assert len(conversation["messages"]) == 2
        assert conversation["messages"][0]["role"] == "user"
        assert conversation["messages"][1]["role"] == "assistant"
        assert conversation["messages"][1]["sources"]
        assert conversation["messages"][1]["events"]

    def test_stream_appends_to_an_existing_conversation(self, client) -> None:
        """Regression: the agent and the API must share one store instance."""
        created = client.post("/api/conversations", json={"title": "Existing"}).json()
        conversation_id = created["id"]

        response = client.post(
            "/api/chat/stream",
            json={"message": "Follow up question", "conversation_id": conversation_id},
        )
        events = parse_sse(response.text)
        started = next(data for name, data in events if name == "agent_started")
        assert started["data"]["conversation_id"] == conversation_id

        conversation = client.get(f"/api/conversations/{conversation_id}").json()
        assert len(conversation["messages"]) == 2
        assert conversation["messages"][0]["content"] == "Follow up question"
        assert conversation["messages"][1]["role"] == "assistant"
        assert conversation["messages"][1]["content"]

    def test_clearing_messages_keeps_the_conversation(self, client) -> None:
        created = client.post("/api/conversations", json={}).json()
        response = client.delete(f"/api/conversations/{created['id']}/messages")
        assert response.status_code == 200
        assert response.json()["messages"] == []
        assert client.get(f"/api/conversations/{created['id']}").status_code == 200
