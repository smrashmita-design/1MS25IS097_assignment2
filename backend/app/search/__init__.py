"""Search provider abstraction.

Every provider performs a **real** web search and returns normalised
:class:`SearchResult` records. The agent never sees provider-specific payloads
and the active provider can be swapped through configuration alone.
"""

from __future__ import annotations

from app.search.base import (
    SearchProvider,
    SearchProviderError,
    SearchQuery,
    SearchResult,
)

__all__ = [
    "SearchProvider",
    "SearchProviderError",
    "SearchQuery",
    "SearchResult",
]
