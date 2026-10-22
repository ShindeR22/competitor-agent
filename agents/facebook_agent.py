"""Facebook Posts + Running Ads. Bundled into one agent because both live
behind the same data sources in practice: Meta Graph API (owned pages only)
or Meta Ad Library (public, no auth needed for basic ad search) plus web
search as a fallback for organic posts.
"""
from __future__ import annotations

from agents.base_agent import Agent, load_prompt
from utils import llm, web


class FacebookAgent(Agent):
    name = "facebook_agent"

    def run(self, competitor: dict) -> dict[str, str]:
        name = competitor["name"]
        out = {}

        try:
            post_results = web.search(f'site:facebook.com "{name}"', num=8)
            post_snippets = "\n".join(f"- {r['title']}: {r['snippet']}" for r in post_results if r.get("snippet"))
            out["Facebook Posts"] = llm.ask(
                load_prompt("facebook_agent.md").format(competitor=name, search_results=post_snippets)
            ).strip() if post_snippets else f"_No recent Facebook posts found for {name}._"
        except web.DataSourceUnavailable:
            out["Facebook Posts"] = "_SERPAPI_KEY not configured — cannot search Facebook posts._"

        out["Running Ads"] = self._ads(competitor)
        return out

    def _ads(self, competitor: dict) -> str:
        """The Meta Ad Library (facebook.com/ads/library) is public and searchable,
        but has no simple unauthenticated REST endpoint for scripted use — it
        requires the Ad Library API with an approved access token. Until
        FACEBOOK_AD_LIBRARY_TOKEN is configured, fall back to a direct link
        + web-search-based signal so the report still flags active campaigns."""
        name = competitor["name"]
        try:
            results = web.search(f'"{name}" site:facebook.com/ads/library OR "sponsored"', num=5)
        except web.DataSourceUnavailable:
            results = None

        link = f"https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=ALL&q={name.replace(' ', '%20')}"
        if not results:
            return (
                f"_No Ad Library API token configured (FACEBOOK_AD_LIBRARY_TOKEN) and/or no SERPAPI_KEY. "
                f"Manually check: {link}_"
            )
        snippets = "\n".join(f"- {r['title']}: {r['snippet']}" for r in results if r.get("snippet"))
        if not snippets:
            return f"_No ad signals found via search. Manually check: {link}_"
        return llm.ask(
            load_prompt("ads_agent.md").format(competitor=name, search_results=snippets, ad_library_link=link)
        ).strip()
