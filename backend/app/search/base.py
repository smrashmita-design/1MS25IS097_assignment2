"""Core search abstractions shared by every provider implementation."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from urllib.parse import urlparse


class SearchProviderError(RuntimeError):
    """Raised when a search backend fails in a way the agent must observe."""

    def __init__(self, message: str, *, recoverable: bool = True) -> None:
        super().__init__(message)
        self.message = message
        self.recoverable = recoverable


@dataclass(slots=True)
class SearchResult:
    """A normalised search hit."""

    title: str
    url: str
    snippet: str = ""
    source: str = ""
    domain: str = ""
    published_at: str | None = None
    score: float = 0.0
    rank: int = 0

    def __post_init__(self) -> None:
        if not self.domain and self.url:
            self.domain = _extract_domain(self.url)
        if not self.source and self.domain:
            self.source = self.domain

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "source": self.source,
            "domain": self.domain,
            "published_at": self.published_at,
            "rank": self.rank,
        }


@dataclass(slots=True)
class SearchQuery:
    """Normalised search request."""

    query: str
    max_results: int = 8
    recency: str | None = None
    extra: dict[str, object] = field(default_factory=dict)


class SearchProvider(abc.ABC):
    """Interface every search backend must implement."""

    name: str = "abstract"
    label: str = "Abstract provider"
    requires_api_key: bool = False

    @abc.abstractmethod
    async def search(self, query: SearchQuery) -> list[SearchResult]:
        """Execute a real search and return normalised results."""

    async def health(self) -> tuple[bool, str]:
        """Return ``(reachable, detail)`` used by the status endpoint."""
        return True, "provider available"


def _extract_domain(url: str) -> str:
    """Return a human friendly domain for a URL."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return ""
    host = parsed.netloc.lower()
    if not host:
        return ""
    if host.startswith("www."):
        host = host[4:]
    return host.split(":")[0]
