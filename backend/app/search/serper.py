"""Serper.dev search provider (requires ``SERPER_API_KEY``)."""

from __future__ import annotations

import logging

import httpx

from app.search.base import SearchProvider, SearchProviderError, SearchQuery, SearchResult

logger = logging.getLogger(__name__)

_ENDPOINT = "https://google.serper.dev/search"


class SerperProvider(SearchProvider):
    """Google results via the Serper.dev API."""

    name = "serper"
    label = "Serper.dev (Google results)"
    requires_api_key = True

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        body: dict[str, object] = {"q": query.query, "num": query.max_results}
        if query.recency:
            body["tbs"] = query.recency
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    _ENDPOINT,
                    json=body,
                    headers={"X-API-KEY": self._api_key, "Content-Type": "application/json"},
                )
                if response.status_code == 401:
                    raise SearchProviderError("Serper API key was rejected.", recoverable=False)
                response.raise_for_status()
                data = response.json()
        except SearchProviderError:
            raise
        except Exception as exc:
            raise SearchProviderError(f"Serper search failed: {exc}") from exc

        raw_items = data.get("organic") or []
        results: list[SearchResult] = []
        for index, item in enumerate(raw_items[: query.max_results]):
            url = item.get("link") or ""
            if not url:
                continue
            results.append(
                SearchResult(
                    title=item.get("title") or url,
                    url=url,
                    snippet=item.get("snippet") or "",
                    published_at=item.get("date"),
                    score=float(item.get("position") or (index + 1)),
                    rank=index + 1,
                )
            )
        if not results:
            raise SearchProviderError("Serper returned no organic results.")
        return results

    async def health(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    _ENDPOINT,
                    json={"q": "nexus connectivity test"},
                    headers={"X-API-KEY": self._api_key},
                )
            if response.status_code in (401, 403):
                return False, "Serper API key was rejected."
            return True, "Serper reachable"
        except Exception as exc:  # pragma: no cover - network dependent
            return False, str(exc)[:120]
