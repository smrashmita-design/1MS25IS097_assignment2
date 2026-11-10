"""Deterministic UI test harness (development only).

Runs the **real** NEXUS FastAPI application with a scripted model so the
frontend can be exercised end-to-end — live SSE streaming, tool observations,
the execution timeline and the final rendered answer — without spending any
Gemini quota or hitting the live search engines.

This file lives under ``tests/`` and is never imported by the application.

    python -m uvicorn tests.ui_harness:app --port 8010
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Any

from google.genai import types

from app.agent.controller import AgentController
from app.api import deps
from app.config import Settings
from app.llm.client import LLMClient, ModelTurn, ToolCall
from app.main import app as fastapi_app
from app.search.base import SearchProvider, SearchQuery, SearchResult
from app.services.conversation_store import InMemoryConversationStore

RESULTS = [
    SearchResult(
        title="Comparing Open-Source AI Agent Frameworks (2026)",
        url="https://example.com/agent-frameworks",
        snippet="A practical comparison of LangGraph, CrewAI, AutoGen and PydanticAI.",
        domain="example.com",
        rank=1,
    ),
    SearchResult(
        title="Building reliable agents with tool calling",
        url="https://docs.example.org/agents/tools",
        snippet="How to design a ReAct loop with explicit observations.",
        domain="docs.example.org",
        rank=2,
    ),
    SearchResult(
        title="Evaluating research agents",
        url="https://blog.example.net/eval-agents",
        snippet="Measuring citation quality in retrieval-augmented research agents.",
        domain="blog.example.net",
        rank=3,
    ),
]

FINAL_ANSWER = """\
## The short answer

The strongest **open-source agent frameworks** right now fall into three
families: graph-based orchestrators, role-based multi-agent systems and
typed, minimal runtimes.

| Framework | Style | Best for |
| --- | --- | --- |
| LangGraph | Explicit graph | Stateful, resumable workflows |
| CrewAI | Role-based crews | Multi-agent collaboration |
| PydanticAI | Typed, minimal | Small, testable agents |

### How to choose

1. Start with **PydanticAI** when the agent is small and you want typed tool
   contracts [docs.example.org](https://docs.example.org/agents/tools).
2. Move to **LangGraph** once you need durable state and human-in-the-loop
   checkpoints [example.com](https://example.com/agent-frameworks).
3. Use **CrewAI** only when genuinely independent roles must collaborate
   [blog.example.net](https://blog.example.net/eval-agents).

> Rule of thumb: pick the simplest framework that supports the state you need.
"""


class ScriptedLLM(LLMClient):
    """Replays a fixed script of tool calls followed by a final answer."""

    model = "scripted-model"

    def __init__(self) -> None:
        self._stage = 0

    def build_tools(self) -> list[types.Tool]:
        return []

    async def stream_turn(
        self,
        contents: Sequence[types.Content],
        *,
        tools: list[types.Tool],
        system_instruction: str,
    ) -> AsyncIterator[ModelTurn]:
        self._stage += 1
        if self._stage == 1:
            yield ModelTurn(
                function_calls=[
                    ToolCall(
                        id="call-1",
                        name="web_search",
                        args={"query": "best open source AI agent frameworks 2026"},
                    )
                ],
                finish_reason="STOP",
            )
            return
        if self._stage == 2:
            yield ModelTurn(
                function_calls=[
                    ToolCall(
                        id="call-2",
                        name="web_search",
                        args={"query": "LangGraph vs CrewAI vs PydanticAI comparison"},
                    )
                ],
                finish_reason="STOP",
            )
            return
        for word in FINAL_ANSWER.split(" "):
            yield ModelTurn(text=word + " ", finish_reason="STOP")
            await asyncio.sleep(0.01)

    async def generate(self, contents, *, tools=None, system_instruction=None) -> ModelTurn:
        return ModelTurn(text="ok")

    async def list_models(self) -> list[str]:
        return ["scripted-model"]

    async def ping(self) -> tuple[bool, str]:
        return True, "scripted model reachable"


class ScriptedSearchProvider(SearchProvider):
    """Returns a fixed, realistic result set."""

    name = "scripted"
    label = "Scripted provider (UI harness)"

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        await asyncio.sleep(0.15)
        return list(RESULTS)

    async def health(self) -> tuple[bool, str]:
        return True, "scripted provider ready"


def build_harness_app() -> Any:
    settings = Settings(
        gemini_api_key="scripted-key",
        gemini_model="scripted-model",
        search_provider="duckduckgo",
        persistence_enabled=False,
        max_agent_iterations=6,
        max_search_results=5,
    )
    store = InMemoryConversationStore()
    controller = AgentController(
        settings=settings,
        llm=ScriptedLLM(),
        search_provider=ScriptedSearchProvider(),
        store=store,
    )

    fastapi_app.dependency_overrides[deps.get_controller] = lambda: controller
    fastapi_app.dependency_overrides[deps.get_store] = lambda: store
    fastapi_app.dependency_overrides[deps.get_app_settings] = lambda: settings
    return fastapi_app


app = build_harness_app()
