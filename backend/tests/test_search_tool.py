"""Tests for the search tool and the tool registry."""

from __future__ import annotations

import pytest

from app.search.base import SearchProviderError
from app.tools.base import ToolError
from app.tools.registry import ToolRegistry
from app.tools.search_tool import SearchToolArgs, build_search_tool
from tests.conftest import FakeSearchProvider, make_results


def build_registry(provider) -> ToolRegistry:
    registry = ToolRegistry()
    spec, validator = build_search_tool(provider)
    registry.register(spec, validator)
    return registry


class TestToolArgumentValidation:
    def test_valid_arguments_are_normalised(self) -> None:
        args = SearchToolArgs.model_validate({"query": "fastapi vs flask"})
        assert args.query == "fastapi vs flask"
        assert args.max_results is None

    def test_missing_query_is_rejected(self) -> None:
        with pytest.raises(Exception):
            SearchToolArgs.model_validate({})

    def test_empty_query_is_rejected(self) -> None:
        with pytest.raises(Exception):
            SearchToolArgs.model_validate({"query": ""})

    def test_out_of_range_max_results_is_rejected(self) -> None:
        with pytest.raises(Exception):
            SearchToolArgs.model_validate({"query": "x", "max_results": 99})

    def test_registry_rejects_invalid_arguments(self) -> None:
        registry = build_registry(FakeSearchProvider(make_results()))
        with pytest.raises(ToolError):
            registry.validate("web_search", {"query": "x", "max_results": 999})

    async def test_registry_reports_invalid_arguments_without_raising(self) -> None:
        registry = build_registry(FakeSearchProvider(make_results()))
        result = await registry.execute("web_search", {"max_results": 3})
        assert result.ok is False
        assert "query" in (result.error or "").lower()


class TestToolExecution:
    async def test_tool_returns_real_results(self) -> None:
        provider = FakeSearchProvider(make_results(2))
        registry = build_registry(provider)
        result = await registry.execute("web_search", {"query": "test query"})
        assert result.ok is True
        assert result.output["result_count"] == 2
        assert result.output["results"][0]["url"] == "https://example.com/article-1"
        assert provider.queries == ["test query"]

    async def test_tool_reports_search_failure(self) -> None:
        provider = FakeSearchProvider(error=SearchProviderError("upstream exploded"))
        registry = build_registry(provider)
        result = await registry.execute("web_search", {"query": "test query"})
        assert result.ok is False
        assert "upstream exploded" in (result.error or "")
        assert result.to_model_payload()["status"] == "error"

    async def test_unknown_tool_is_reported(self) -> None:
        registry = build_registry(FakeSearchProvider(make_results()))
        result = await registry.execute("does_not_exist", {})
        assert result.ok is False
        assert "Unknown tool" in (result.error or "")

    async def test_no_results_is_treated_as_failure(self) -> None:
        registry = build_registry(FakeSearchProvider([]))
        result = await registry.execute("web_search", {"query": "nothing"})
        assert result.ok is False

    async def test_tool_records_duration(self) -> None:
        registry = build_registry(FakeSearchProvider(make_results(1)))
        result = await registry.execute("web_search", {"query": "test"})
        assert result.duration_ms >= 0


class TestToolDeclarations:
    def test_registry_exposes_google_compatible_declarations(self) -> None:
        registry = build_registry(FakeSearchProvider(make_results()))
        tools = registry.declarations()
        assert len(tools) == 1
        declaration = tools[0].function_declarations[0]
        assert declaration.name == "web_search"
        assert "query" in declaration.parameters.properties
        assert declaration.parameters.required == ["query"]
