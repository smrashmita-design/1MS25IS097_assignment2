"""Real web search powered by Gemini's Google Search grounding.

The provider asks Gemini to answer with the ``google_search`` tool enabled, then
harvests the grounding metadata (search queries, source URLs and the excerpts
the model relied on) into normalised :class:`SearchResult` records.

Grounding URLs point at a Google redirect; they are canonicalised against the
live page so citations expose a clean URL, title and description.
"""

from __future__ import annotations

import logging
from typing import Any

from google.genai import types

from app.llm.client import LLMClient, LLMError
from app.search.base import SearchProvider, SearchProviderError, SearchQuery, SearchResult
from app.search.resolve import resolve_pages

logger = logging.getLogger(__name__)

_GROUNDING_PROMPT = (
    "Use Google Search to find current, reliable sources for the user's query. "
    "List the most relevant sources and briefly summarise what each one says. "
    "Prefer authoritative and recent sources."
)


class GoogleGroundingProvider(SearchProvider):
    """Search backend that performs an actual Google search through Gemini."""

    name = "google_grounding"
    label = "Google Search (Gemini grounding)"
    requires_api_key = True

    def __init__(self, llm: LLMClient, *, max_resolutions: int = 6) -> None:
        self._llm = llm
        self._max_resolutions = max_resolutions

    # ------------------------------------------------------------ helpers --
    @staticmethod
    def _supports(metadata: Any) -> list[tuple[str, str]]:
        """Map grounding chunks to their supporting excerpt text."""
        pairs: list[tuple[str, str]] = []
        for support in getattr(metadata, "grounding_supports", None) or []:
            segment = getattr(support, "segment", None)
            text = _clean(getattr(segment, "text", None) or "")
            indices = list(getattr(support, "grounding_chunk_indices", None) or [])
            for index in indices:
                pairs.append((str(index), text))
        return pairs

    # ------------------------------------------------------------- search --
    async def search(self, query: SearchQuery) -> list[SearchResult]:
        tools = [types.Tool(google_search=types.GoogleSearch(**_time_filter(query.recency)))]
        try:
            turn = await self._llm.generate(
                f"Search the web for: {query.query}\n\n{_GROUNDING_PROMPT}",
                tools=tools,
                system_instruction=(
                    "You are a web research assistant. Always ground your answer in "
                    "Google Search results and never invent sources."
                ),
            )
        except LLMError as exc:
            raise SearchProviderError(f"Google grounding search failed: {exc.message}") from exc

        metadata = turn.grounding_metadata
        chunks = [c for c in (getattr(metadata, "grounding_chunks", None) or []) if getattr(c, "web", None)]
        if not chunks:
            raise SearchProviderError(
                "Google Search returned no grounding sources for this query.",
                recoverable=True,
            )

        supports = self._supports(metadata)
        by_index: dict[int, str] = {}
        for raw_index, text in supports:
            try:
                by_index[int(raw_index)] = text
            except ValueError:
                continue

        results: list[SearchResult] = []
        seen_urls: set[str] = set()
        for position, chunk in enumerate(chunks):
            web = chunk.web
            url = (getattr(web, "uri", None) or "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = _clean(getattr(web, "title", None) or "") or url
            domain = _clean(getattr(web, "domain", None) or "")
            snippet = by_index.get(position, "")
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    source=domain or title,
                    domain=domain,
                    rank=position + 1,
                )
            )

        await self._enrich(results)

        results.sort(key=lambda r: r.rank)
        return results[: query.max_results]

    async def _enrich(self, results: list[SearchResult]) -> None:
        """Resolve redirect URLs into canonical URLs with readable titles."""
        targets = results[: self._max_resolutions]
        if not targets:
            return
        try:
            resolved = await resolve_pages([r.url for r in targets])
        except Exception as exc:  # pragma: no cover - network dependent
            logger.debug("URL canonicalisation failed: %s", exc)
            return
        for result in targets:
            page = resolved.get(result.url)
            if not page or not page.ok:
                continue
            if page.url:
                result.url = page.url
            if page.title:
                result.title = page.title
            if page.description and not result.snippet:
                result.snippet = page.description

    # ------------------------------------------------------------- status --
    async def health(self) -> tuple[bool, str]:
        reachable, detail = await self._llm.ping()
        return reachable, detail


def _clean(value: str | None) -> str:
    import re

    return re.sub(r"\s+", " ", value or "").strip()


_RECENCY_WINDOWS = {
    "day": 1,
    "week": 7,
    "month": 31,
    "year": 365,
}


def _time_filter(recency: str | None) -> dict[str, object]:
    """Translate a recency keyword into a Google Search time range filter."""
    days = _RECENCY_WINDOWS.get((recency or "").lower())
    if not days:
        return {}
    from datetime import datetime, timedelta, timezone

    start = datetime.now(timezone.utc) - timedelta(days=days)
    return {"time_range_filter": types.Interval(start_time=start.isoformat())}
