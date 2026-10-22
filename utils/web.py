"""Fetching and searching helpers shared by every agent.

Design note: this project intentionally has no hard dependency on any one
search/social API. `search()` uses SerpAPI when SERPAPI_KEY is set, and
raises a clear, catchable error otherwise so agents can fall back to
LLM-only reasoning instead of crashing the whole run.
"""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup

from utils.config import env

UA = "Mozilla/5.0 (compatible; ShutterCloudCompetitorAgent/1.0; +https://shuttercloud.ai)"


class DataSourceUnavailable(Exception):
    """Raised when an agent needs an API key that isn't configured."""


def fetch_html(url: str, timeout: int = 15) -> str | None:
    try:
        resp = requests.get(url, headers={"User-Agent": UA}, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException:
        return None


def fetch_text(url: str, timeout: int = 15) -> str | None:
    """Fetch a page and return visible, whitespace-normalized text (scripts/styles stripped)."""
    html = fetch_html(url, timeout=timeout)
    if html is None:
        return None
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def fetch_meta(url: str) -> dict:
    """Grab SEO-relevant tags: title, meta description, meta keywords, h1s."""
    html = fetch_html(url)
    if html is None:
        return {}
    soup = BeautifulSoup(html, "lxml")
    title = soup.title.string.strip() if soup.title and soup.title.string else None
    desc_tag = soup.find("meta", attrs={"name": "description"})
    keywords_tag = soup.find("meta", attrs={"name": "keywords"})
    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")]
    return {
        "title": title,
        "meta_description": desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else None,
        "meta_keywords": keywords_tag["content"].strip() if keywords_tag and keywords_tag.get("content") else None,
        "h1s": h1s,
    }


def search(query: str, num: int = 10) -> list[dict]:
    """Web search via SerpAPI. Returns [{title, link, snippet}, ...].

    Raises DataSourceUnavailable if SERPAPI_KEY isn't configured — callers
    should catch this and degrade gracefully (e.g. skip or note "no data source").
    """
    key = env("SERPAPI_KEY")
    if not key:
        raise DataSourceUnavailable("SERPAPI_KEY not set — cannot perform web search.")
    resp = requests.get(
        "https://serpapi.com/search",
        params={"q": query, "num": num, "api_key": key},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return [
        {"title": r.get("title"), "link": r.get("link"), "snippet": r.get("snippet")}
        for r in data.get("organic_results", [])
    ]
