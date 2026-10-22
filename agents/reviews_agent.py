"""Pulls review signal from G2/Capterra/Trustpilot/app stores (via search,
since none of these expose a free public API for arbitrary competitor
lookups) and has Claude extract likes vs. complaints — the two things
product/marketing actually act on, rather than a raw star-rating dump.
"""
from __future__ import annotations

from agents.base_agent import Agent, load_prompt
from utils import llm, web
from utils.config import load_config


class ReviewsAgent(Agent):
    name = "reviews_agent"

    def run(self, competitor: dict) -> dict[str, str]:
        name = competitor["name"]
        sources = load_config()["review_sources"]
        query = f'"{name}" review ' + " OR ".join(f"site:{s}" for s in sources)

        try:
            results = web.search(query, num=10)
        except web.DataSourceUnavailable:
            note = "_SERPAPI_KEY not configured — cannot pull review-site data._"
            return {"Customer Reviews": note, "User Complaints": note, "User Likes": note}

        if not results:
            note = f"_No review-site results found for {name} this run._"
            return {"Customer Reviews": note, "User Complaints": note, "User Likes": note}

        snippets = "\n".join(f"- {r['title']}: {r['snippet']} ({r['link']})" for r in results if r.get("snippet"))
        prompt = load_prompt("reviews_agent.md").format(competitor=name, search_results=snippets)
        analysis = llm.ask(prompt)
        return _split_llm_sections(analysis)


def _split_llm_sections(text: str) -> dict[str, str]:
    out = {}
    current = None
    buf = []
    for line in text.splitlines():
        if line.startswith("### "):
            if current:
                out[current] = "\n".join(buf).strip()
            current = line[4:].strip()
            buf = []
        else:
            buf.append(line)
    if current:
        out[current] = "\n".join(buf).strip()
    return out
