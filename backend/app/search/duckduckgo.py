"""Keyless web search by scraping DuckDuckGo's HTML endpoint.

Useful as a zero-configuration fallback: it returns genuine titles, URLs and
snippets without requiring any third-party API key.
"""

from __future__ import annotations

import html as html_lib
import logging
import re
import urllib.parse

import httpx

from app.search.base import SearchProvider, SearchProviderError, SearchQuery, SearchResult

logger = logging.getLogger(__name__)

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

_TITLE_RE = re.compile(r'class="result__a"[^>]*>(.*?)</a>', re.S)
_SNIPPET_RE = re.compile(r'class="result__snippet"[^>]*>(.*?)</(?:a|div)>', re.S)
_LINK_RE = re.compile(r'class="result__a" href="(.*?)"', re.S)

# The lite endpoint uses a different markup layout.
_LITE_TITLE_RE = re.compile(r"class='result-link'[^>]*>(.*?)</a>", re.S)
_LITE_SNIPPET_RE = re.compile(r"class='result-snippet'[^>]*>(.*?)</td>", re.S)
_LITE_LINK_RE = re.compile(r"class='result-link' href='(.*?)'", re.S)


def _has_results(markup: str) -> bool:
    """Whether a result page actually contains hits."""
    return bool(_TITLE_RE.findall(markup) or _LITE_TITLE_RE.findall(markup))


def _strip(markup: str) -> str:
    text = re.sub(r"<[^>]+>", "", markup)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _clean_url(url: str) -> str:
    url = html_lib.unescape(url.strip())
    if url.startswith("//"):
        url = "https:" + url
    if "uddg=" in url:
        query = urllib.parse.urlparse(url).query
        params = urllib.parse.parse_qs(query)
        if "uddg" in params:
            return params["uddg"][0]
    return url


class DuckDuckGoProvider(SearchProvider):
    """Scrapes DuckDuckGo's lightweight HTML result page."""

    name = "duckduckgo"
    label = "DuckDuckGo (keyless)"
    requires_api_key = False

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        headers = {"User-Agent": _UA, "Referer": "https://duckduckgo.com/"}
        markup = ""

        try:
            async with httpx.AsyncClient(headers=headers, timeout=25.0, follow_redirects=True) as client:
                response = await client.post("https://html.duckduckgo.com/html/", data={"q": query.query})
                markup = response.text
                if not _has_results(markup):
                    # DuckDuckGo throttles bursts of requests (HTTP 202 with an
                    # empty body). Retry through the lightweight endpoint.
                    lite = await client.get(
                        "https://lite.duckduckgo.com/lite/",
                        params={"q": query.query},
                    )
                    lite_markup = lite.text
                    if _has_results(lite_markup):
                        markup = lite_markup
        except Exception as exc:
            raise SearchProviderError(f"DuckDuckGo search failed: {exc}") from exc

        titles = _TITLE_RE.findall(markup) or _LITE_TITLE_RE.findall(markup)
        links = _LINK_RE.findall(markup) or _LITE_LINK_RE.findall(markup)
        snippets = _SNIPPET_RE.findall(markup) or _LITE_SNIPPET_RE.findall(markup)

        if not titles:
            raise SearchProviderError(
                "DuckDuckGo returned no results for this query (it throttles rapid requests)."
            )

        results: list[SearchResult] = []
        seen: set[str] = set()
        for index, raw_title in enumerate(titles):
            title = _strip(raw_title)
            if not title or index >= len(links):
                continue
            url = _clean_url(links[index])
            if not url.startswith("http") or url in seen:
                continue
            seen.add(url)
            snippet = _strip(snippets[index]) if index < len(snippets) else ""
            results.append(
                SearchResult(
                    title=title,
                    url=url,
                    snippet=snippet,
                    rank=len(results) + 1,
                )
            )
            if len(results) >= query.max_results:
                break
        return results

    async def health(self) -> tuple[bool, str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get("https://duckduckgo.com", follow_redirects=True)
            if response.status_code < 400:
                return True, "DuckDuckGo reachable"
            return False, f"HTTP {response.status_code}"
        except Exception as exc:  # pragma: no cover - network dependent
            return False, str(exc)[:120]
