"""Utility helpers for turning search-engine redirect URLs into clean sources."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_META_DESC_RE = re.compile(
    r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"'](.*?)[\"']", re.S | re.I
)
_META_DESC_RE_ALT = re.compile(
    r"<meta[^>]+content=[\"'](.*?)[\"'][^>]+name=[\"']description[\"']", re.S | re.I
)


@dataclass(slots=True)
class ResolvedPage:
    """Canonical URL plus lightweight page metadata."""

    url: str
    title: str = ""
    description: str = ""
    ok: bool = False


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


async def resolve_page(url: str, client: httpx.AsyncClient) -> ResolvedPage:
    """Follow redirects for ``url`` and extract the page title/description.

    Failures are non-fatal: the original URL is returned so the citation still
    works, only the enriched metadata is lost.
    """
    try:
        response = await client.get(url, timeout=10.0)
        final_url = str(response.url)
        html = response.text[:400_000]
    except Exception as exc:  # pragma: no cover - network dependent
        logger.debug("Could not resolve %s: %s", url, exc)
        return ResolvedPage(url=url, ok=False)

    title = ""
    match = _TITLE_RE.search(html)
    if match:
        title = _clean(match.group(1))[:220]

    description = ""
    desc_match = _META_DESC_RE.search(html) or _META_DESC_RE_ALT.search(html)
    if desc_match:
        description = _clean(desc_match.group(1))[:400]

    return ResolvedPage(url=final_url or url, title=title, description=description, ok=True)


async def resolve_pages(
    urls: list[str],
    *,
    timeout: float = 20.0,
    max_concurrency: int = 6,
) -> dict[str, ResolvedPage]:
    """Resolve many URLs concurrently, keyed by the *original* URL."""
    if not urls:
        return {}
    semaphore = asyncio.Semaphore(max_concurrency)

    async with httpx.AsyncClient(
        headers={"User-Agent": _UA},
        timeout=timeout,
        follow_redirects=True,
    ) as client:

        async def _one(url: str) -> tuple[str, ResolvedPage]:
            async with semaphore:
                return url, await resolve_page(url, client)

        results = await asyncio.gather(*(_one(u) for u in urls), return_exceptions=True)

    out: dict[str, ResolvedPage] = {}
    for item in results:
        if isinstance(item, BaseException):
            continue
        url, page = item
        out[url] = page
    return out
