"""Shared pytest fixtures and fakes."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Sequence
from typing import Any

import pytest

os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("SEARCH_PROVIDER", "duckduckgo")
os.environ.setdefault("PERSISTENCE_ENABLED", "false")

from google.genai import types  # noqa: E402

from app.config import Settings, get_settings  # noqa: E402
from app.llm.client import LLMClient, ModelTurn, ToolCall  # noqa: E402
from app.search.base import SearchProvider, SearchProviderError, SearchQuery, SearchResult  # noqa: E402


@pytest.fixture
def settings() -> Settings:
    """A deterministic settings object for tests."""
    return Settings(
        gemini_api_key="test-key",
        gemini_model="gemini-2.5-flash",
        search_provider="duckduckgo",
        persistence_enabled=False,
        max_agent_iterations=3,
        max_search_results=3,
        store_dir=os.path.join(os.sep, "tmp", "nexus-tests"),
    )


class FakeLLM(LLMClient):
    """A scripted model that replays a fixed list of turns.

    Each entry is either a plain string (assistant text) or a list of
    :class:`ToolCall` objects (the model requesting a tool).
    """

    model = "fake-model"

    def __init__(self, script: Sequence[Any]) -> None:
        self.script = list(script)
        self.calls: list[list[types.Content]] = []
        self.prompts: list[str] = []

    def build_tools(self) -> list[types.Tool]:
        return []

    async def stream_turn(
        self,
        contents: Sequence[types.Content],
        *,
        tools: list[types.Tool],
        system_instruction: str,
    ) -> AsyncIterator[ModelTurn]:
        self.calls.append(list(contents))
        self.prompts.append(system_instruction)
        if not self.script:
            yield ModelTurn(text="No script left.")
            return
        entry = self.script.pop(0)
        if isinstance(entry, str):
            yield ModelTurn(text=entry, finish_reason="STOP")
            return
        yield ModelTurn(function_calls=list(entry), finish_reason="STOP")

    async def generate(self, contents, *, tools=None, system_instruction=None) -> ModelTurn:
        if self.script:
            entry = self.script.pop(0)
            if isinstance(entry, str):
                return ModelTurn(text=entry)
            return ModelTurn(function_calls=list(entry))
        return ModelTurn(text="ok")

    async def list_models(self) -> list[str]:
        return ["gemini-2.5-flash", "gemini-2.5-pro"]

    async def ping(self) -> tuple[bool, str]:
        return True, "fake model reachable"


class FakeSearchProvider(SearchProvider):
    """Search provider that returns canned results or raises."""

    name = "fake"
    label = "Fake provider"

    def __init__(self, results: list[SearchResult] | None = None, error: Exception | None = None) -> None:
        self.results = results or []
        self.error = error
        self.queries: list[str] = []

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        self.queries.append(query.query)
        if self.error is not None:
            raise self.error
        return list(self.results)

    async def health(self) -> tuple[bool, str]:
        return True, "fake provider ready"


def make_results(count: int = 2) -> list[SearchResult]:
    return [
        SearchResult(
            title=f"Result {index + 1}",
            url=f"https://example.com/article-{index + 1}",
            snippet=f"Snippet for result {index + 1}",
            domain="example.com",
            rank=index + 1,
        )
        for index in range(count)
    ]


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
