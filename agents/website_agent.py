"""Crawls a competitor's marketing site (home, pricing, blog, features) and
diffs today's content against yesterday's snapshot so the report only
surfaces *changes*, not a re-summary of the whole site every day.
"""
from __future__ import annotations

import difflib

from agents.base_agent import Agent, load_prompt
from utils import llm, web
from utils.storage import load_previous_snapshot, save_snapshot

CANDIDATE_PATHS = ["", "/pricing", "/blog", "/features", "/product"]


class WebsiteAgent(Agent):
    name = "website_agent"

    def run(self, competitor: dict) -> dict[str, str]:
        base = competitor["website"].rstrip("/")
        pages = {}
        for path in CANDIDATE_PATHS:
            text = web.fetch_text(base + path)
            if text:
                pages[path or "/"] = text[:8000]

        if not pages:
            note = f"_Could not reach {base} today (fetch failed for all candidate paths)._"
            return {
                "Website Changes": note,
                "Company Overview": note,
            }

        combined_today = "\n\n---PAGE BREAK---\n\n".join(
            f"[{p}]\n{txt}" for p, txt in pages.items()
        )
        previous = load_previous_snapshot(competitor["name"], "website")
        save_snapshot(competitor["name"], "website", combined_today)

        diff_summary = "No previous snapshot — this is the first run, treat all content as baseline."
        if previous:
            diff = list(
                difflib.unified_diff(
                    previous.splitlines(), combined_today.splitlines(), lineterm="", n=1
                )
            )
            diff_summary = "\n".join(diff[:400]) if diff else "No textual changes detected since last run."

        prompt = load_prompt("website_agent.md").format(
            competitor=competitor["name"],
            website=base,
            pages_today=combined_today[:12000],
            diff=diff_summary[:6000],
        )
        analysis = llm.ask(prompt)
        sections = _split_llm_sections(analysis)
        return sections


def _split_llm_sections(text: str) -> dict[str, str]:
    """The website_agent prompt asks Claude to emit '### <Section Name>' blocks
    matching the profile's section names — split those back into a dict."""
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
