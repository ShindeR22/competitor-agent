"""Surfaces recent Instagram activity (posts/Reels) for a competitor.

Instagram's official Graph API only exposes data for accounts you manage,
so there's no clean public API for monitoring a *competitor's* account.
This agent uses web search (SerpAPI) as the default data source and is
structured so a Meta Graph API / third-party scraper (Apify, Phyllo, etc.)
can be dropped in later behind the same run() interface.
"""
from __future__ import annotations

from agents.base_agent import Agent, load_prompt
from utils import llm, web
from utils.config import env


class InstagramAgent(Agent):
    name = "instagram_agent"

    def run(self, competitor: dict) -> dict[str, str]:
        handle = competitor.get("instagram")
        if not handle:
            return {"Instagram Posts & Reels": "_No Instagram handle configured for this competitor._"}

        try:
            results = web.search(f'site:instagram.com/{handle}', num=10)
        except web.DataSourceUnavailable:
            return {
                "Instagram Posts & Reels": (
                    f"_SERPAPI_KEY not configured — cannot pull recent posts for @{handle}. "
                    f"Set SERPAPI_KEY in .env, or wire in Meta Graph API / Apify for full post data._"
                )
            }

        if not results:
            return {"Instagram Posts & Reels": f"_No recent public search results found for @{handle}._"}

        snippets = "\n".join(f"- {r['title']}: {r['snippet']}" for r in results if r.get("snippet"))
        prompt = load_prompt("instagram_agent.md").format(
            competitor=competitor["name"], handle=handle, search_results=snippets
        )
        return {"Instagram Posts & Reels": llm.ask(prompt).strip()}
