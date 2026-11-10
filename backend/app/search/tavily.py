"""Tavily search provider (requires ``TAVILY_API_KEY``).

Tavily is purpose-built for agents: it returns clean results with an optional
LLM-friendly answer and relevance scores.
"""

from __future__ import annotations

import logging

import httpx

from app.search.base import SearchProvider, SearchProviderError, SearchQuery, SearchResult

logger = logging.getLogger(__name__)

_ENDPOINT = "https://api.tavily.com/search"

_RECENCY_MAP = {
    "day": "day",
    "week": "week",
    "month": "month",
    "year": "year",
}


class TavilyProvider(SearchProvider):
    """Agent-oriented web search API."""

    name = "tavily"
    label = "Tavily (agent search)"
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        body: dict[str, object] = {
            "api_key": self._api_key,
            "query": query.query,
            "max_results": query.max_results,
            "search_depth": "advanced",
            "include_answer": False,
        }
        if query.recency in _RECENCY_MAP:
            body["days"] = {"day": 1, "week": 7, "month": 30, "year": 365}[query.recency]
        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                response = await client.post(_ENDPOINT, json=body)
                if response.status_code in (401, 403):
                    raise SearchProviderError("Tavily API key was rejected.", recoverable=False)
                response.raise_for_status()
                data = response.json()
        except SearchProviderError:
            raise
        except Exception as exc:
            raise SearchProviderError(f"Tavily search failed: {exc}") from exc

        raw_items = data.get("results") or []
        results: list[SearchResult] = []
        for index, item in enumerate(raw_items[: query.max_results]):
            url = item.get("url") or ""
            if not url:
                continue
            results.append(
                SearchResult(
                    title=item.get("title") or url,
                    url=url,
                    snippet=item.get("content") or "",
                    published_at=item.get("published_date"),
                    score=float(item.get("score") or 0.0),
                    rank=index + 1,
                )
            )
        if not results:
            raise SearchProviderError("Tavily returned no results.")
        return results

    async def health(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    _ENDPOINT,
                    json={"api_key": self._api_key, "query": "nexus connectivity test", "max_results": 1},
                )
            if response.status_code in (401, 403):
                return False, "Tavily API key was rejected."
            return True, "Tavily reachable"
        except Exception as exc:  # pragma: no cover - network dependent
            return False, str(exc)[:120]
