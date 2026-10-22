"""Infers a competitor's SEO keyword focus from on-page signals (title, meta
description/keywords, H1s) plus, when SERPAPI_KEY is available, what queries
actually surface them. This is directional, not a substitute for Ahrefs/
SEMrush — swap in a real rank-tracking API here if/when the team licenses one.
"""
from __future__ import annotations

from agents.base_agent import Agent, load_prompt
from utils import llm, web


class SEOAgent(Agent):
    name = "seo_agent"

    def run(self, competitor: dict) -> dict[str, str]:
        base = competitor["website"].rstrip("/")
        meta = web.fetch_meta(base)
        if not meta:
            return {"SEO Keywords": f"_Could not fetch {base} to inspect SEO metadata._"}

        serp_context = ""
        try:
            results = web.search(f'{competitor["name"]} photography client gallery software', num=5)
            serp_context = "\n".join(f"- {r['title']}: {r['snippet']}" for r in results if r.get("snippet"))
        except web.DataSourceUnavailable:
            serp_context = "_SERPAPI_KEY not configured — no live SERP context, using on-page metadata only._"

        prompt = load_prompt("seo_agent.md").format(
            competitor=competitor["name"],
            title=meta.get("title") or "n/a",
            description=meta.get("meta_description") or "n/a",
            keywords=meta.get("meta_keywords") or "n/a",
            h1s=", ".join(meta.get("h1s") or []) or "n/a",
            serp_context=serp_context,
        )
        return {"SEO Keywords": llm.ask(prompt).strip()}
