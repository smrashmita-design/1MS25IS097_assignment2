"""Search provider factory.

Chooses the concrete search backend from configuration and guarantees that the
selected backend is actually usable with the secrets currently available.
"""

from __future__ import annotations

import logging

from app.config import Settings, get_settings
from app.llm.client import LLMClient
from app.search.base import SearchProvider, SearchProviderError
from app.search.duckduckgo import DuckDuckGoProvider
from app.search.fallback import FallbackSearchProvider
from app.search.google_grounding import GoogleGroundingProvider
from app.search.serper import SerperProvider
from app.search.tavily import TavilyProvider

logger = logging.getLogger(__name__)

AVAILABLE_PROVIDERS = ("google_grounding", "duckduckgo", "serper", "tavily")


def _build_primary(
    settings: Settings,
    llm: LLMClient | None,
) -> SearchProvider:
    """Instantiate the configured provider, raising if it cannot be used."""
    provider = settings.search_provider
    match provider:
        case "google_grounding":
            if not settings.gemini_configured:
                raise SearchProviderError(
                    "google_grounding requires GEMINI_API_KEY.", recoverable=False
                )
            if llm is None:
                raise SearchProviderError("A Gemini client is required for grounding.", recoverable=False)
            return GoogleGroundingProvider(llm, max_resolutions=settings.max_url_resolutions)

        case "duckduckgo":
            return DuckDuckGoProvider()

        case "serper":
            key = settings.serper_api_key
            if not key or not key.get_secret_value().strip():
                raise SearchProviderError("SERPER_API_KEY is not configured.", recoverable=False)
            return SerperProvider(key.get_secret_value())

        case "tavily":
            key = settings.tavily_api_key
            if not key or not key.get_secret_value().strip():
                raise SearchProviderError("TAVILY_API_KEY is not configured.", recoverable=False)
            return TavilyProvider(key.get_secret_value())

        case _:
            raise SearchProviderError(f"Unknown search provider '{provider}'.", recoverable=False)


def build_search_provider(
    settings: Settings | None = None,
    llm: LLMClient | None = None,
) -> SearchProvider:
    """Instantiate the configured search provider.

    The preferred backend is always attempted first. If it is unusable with the
    current credentials we fall back to the keyless DuckDuckGo backend, and the
    provider is additionally wrapped so that a runtime failure degrades to the
    same fallback rather than aborting the agent run.
    """
    settings = settings or get_settings()

    try:
        primary = _build_primary(settings, llm)
    except SearchProviderError:
        logger.warning(
            "Search provider '%s' is unavailable; falling back to the keyless DuckDuckGo backend.",
            settings.search_provider,
        )
        primary = DuckDuckGoProvider()

    if primary.name == "duckduckgo":
        return primary
    return FallbackSearchProvider(primary, [DuckDuckGoProvider()])
