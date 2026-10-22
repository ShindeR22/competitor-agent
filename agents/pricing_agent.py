"""Focused pricing-page watcher. Kept separate from website_agent because
pricing changes are high-signal and deserve their own diff + dedicated prompt
rather than being buried in a general site crawl.
"""
from __future__ import annotations

import difflib

from agents.base_agent import Agent, load_prompt
from utils import llm, web
from utils.storage import load_previous_snapshot, save_snapshot

PRICING_PATHS = ["/pricing", "/plans", "/price", "/pricing-plans"]


class PricingAgent(Agent):
    name = "pricing_agent"

    def run(self, competitor: dict) -> dict[str, str]:
        base = competitor["website"].rstrip("/")
        text = None
        used_path = None
        for path in PRICING_PATHS:
            text = web.fetch_text(base + path)
            if text:
                used_path = path
                break

        if not text:
            return {"Pricing Changes": "_No pricing page found at common paths (/pricing, /plans, /price)._"}

        text = text[:10000]
        previous = load_previous_snapshot(competitor["name"], "pricing")
        save_snapshot(competitor["name"], "pricing", text)

        if not previous:
            diff_summary = "No previous snapshot — first run, report current pricing as baseline."
        else:
            diff = list(difflib.unified_diff(previous.splitlines(), text.splitlines(), lineterm="", n=1))
            diff_summary = "\n".join(diff[:300]) if diff else "No changes detected since last run."

        prompt = load_prompt("pricing_agent.md").format(
            competitor=competitor["name"],
            url=base + used_path,
            pricing_text=text,
            diff=diff_summary[:4000],
        )
        return {"Pricing Changes": llm.ask(prompt).strip()}
