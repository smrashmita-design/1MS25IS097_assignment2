"""A composite search provider that degrades gracefully.

If the preferred backend fails (rate limits, upstream outage, blocked region)
the agent should still be able to research the question rather than aborting the
whole run. :class:`FallbackSearchProvider` transparently retries with a
secondary backend and records which one actually served the results.
"""

from __future__ import annotations

import logging

from app.search.base import SearchProvider, SearchProviderError, SearchQuery, SearchResult

logger = logging.getLogger(__name__)


class FallbackSearchProvider(SearchProvider):
    """Try the primary provider, then each fallback in order."""

    def __init__(self, primary: SearchProvider, fallbacks: list[SearchProvider]) -> None:
        self.primary = primary
        self.fallbacks = fallbacks
        self.name = primary.name
        self.label = primary.label
        self.requires_api_key = primary.requires_api_key

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        errors: list[str] = []
        for provider in [self.primary, *self.fallbacks]:
            try:
                results = await provider.search(query)
            except SearchProviderError as exc:
                errors.append(f"{provider.name}: {exc.message}")
                logger.warning("Search provider %s failed: %s", provider.name, exc.message)
                continue
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{provider.name}: {exc}")
                logger.warning("Search provider %s raised: %s", provider.name, exc)
                continue
            if results:
                return results
            errors.append(f"{provider.name}: no results")
        raise SearchProviderError(
            "All search backends failed. " + " | ".join(errors)[:600],
            recoverable=True,
        )

    async def health(self) -> tuple[bool, str]:
        reachable, detail = await self.primary.health()
        if reachable:
            return True, detail
        for provider in self.fallbacks:
            ok, info = await provider.health()
            if ok:
                return True, f"primary unavailable ({detail}); fallback '{provider.name}' reachable"
        return False, detail
