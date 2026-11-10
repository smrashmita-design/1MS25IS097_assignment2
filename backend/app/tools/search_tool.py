"""The ``web_search`` tool — the agent's action space.

The model decides *whether* and *what* to search; this module performs the real
network search and shapes the observations returned to the model.
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from google.genai import types
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.search.base import SearchProvider, SearchProviderError, SearchQuery, SearchResult
from app.tools.base import ToolResult, ToolSpec

logger = logging.getLogger(__name__)

TOOL_NAME = "web_search"


class SearchToolArgs(BaseModel):
    """Validation schema for the ``web_search`` tool arguments."""

    query: str = Field(
        min_length=2,
        max_length=512,
        description="The search query to send to the web search engine.",
    )
    max_results: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description="How many results to return. Defaults to the server configuration.",
    )
    recency: Literal["day", "week", "month", "year"] | None = Field(
        default=None,
        description="Optionally restrict results to a recent time window.",
    )


def _result_payload(results: list[SearchResult], provider: str) -> dict[str, Any]:
    """Shape the observation handed back to the model."""
    return {
        "provider": provider,
        "result_count": len(results),
        "results": [
            {
                "position": item.rank,
                "title": item.title,
                "url": item.url,
                "snippet": item.snippet,
                "domain": item.domain,
                "published_at": item.published_at,
            }
            for item in results
        ],
    }


def build_search_tool(
    provider: SearchProvider,
    settings: Settings | None = None,
) -> tuple[ToolSpec, type[BaseModel]]:
    """Create the ``web_search`` :class:`ToolSpec` bound to ``provider``."""
    settings = settings or get_settings()

    async def _handler(args: dict[str, Any]) -> ToolResult:
        query_text = str(args.get("query", "")).strip()
        if not query_text:
            return ToolResult(ok=False, error="`query` is required.", display="Missing search query")

        limit = int(args.get("max_results") or settings.max_search_results)
        limit = max(1, min(limit, settings.max_search_results))

        request = SearchQuery(query=query_text, max_results=limit, recency=args.get("recency"))
        try:
            results = await provider.search(request)
        except SearchProviderError as exc:
            logger.warning("Search provider failed: %s", exc.message)
            return ToolResult(
                ok=False,
                error=exc.message,
                display=f"Search failed for “{query_text}”",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected search failure")
            return ToolResult(
                ok=False,
                error=f"{type(exc).__name__}: {exc}"[:400],
                display=f"Search failed for “{query_text}”",
            )

        if not results:
            return ToolResult(
                ok=False,
                error=f"No results were returned for '{query_text}'.",
                display=f"No results for “{query_text}”",
            )

        payload = _result_payload(results, provider.name)
        top = results[0]
        return ToolResult(
            ok=True,
            output=payload,
            display=f"{len(results)} results for “{query_text}” — top source: {top.domain or top.source}",
        )

    spec = ToolSpec(
        name=TOOL_NAME,
        label="Web search",
        description=(
            "Search the live web for current information. Use this whenever the answer "
            "depends on facts you cannot verify from your own knowledge: recent events, "
            "statistics, product comparisons, documentation, pricing, or anything that may "
            "have changed. Call it with a specific, self-contained search query. "
            "You may call it multiple times with different queries to cover different "
            "aspects of the question before answering."
        ),
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "query": types.Schema(
                    type="STRING",
                    description="A specific search query, e.g. 'FastAPI vs Flask production benchmarks 2026'.",
                ),
                "max_results": types.Schema(
                    type="INTEGER",
                    description="Maximum number of results to return (1-20).",
                ),
                "recency": types.Schema(
                    type="STRING",
                    description="Optional time filter: day, week, month or year.",
                ),
            },
            required=["query"],
        ),
        handler=_handler,
    )
    return spec, SearchToolArgs
