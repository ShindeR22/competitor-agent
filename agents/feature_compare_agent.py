"""Runs last: reads what every other agent already wrote into the
competitor's profile (Company Overview, New Features, AI Features, Pricing)
and produces a feature-by-feature comparison against ShutterCloud, plus
Strengths/Weaknesses. Kept separate from website_agent so it always reasons
over the *complete* picture for the day, not just the site crawl.
"""
from __future__ import annotations

from agents.base_agent import Agent, load_prompt
from utils import llm
from utils.config import shuttercloud_features
from utils.storage import parse_sections, read_profile


class FeatureCompareAgent(Agent):
    name = "feature_compare_agent"

    def run(self, competitor: dict) -> dict[str, str]:
        existing = parse_sections(read_profile(competitor["name"]))
        context = "\n\n".join(
            f"## {section}\n{existing.get(section, '_No data yet._')}"
            for section in [
                "Company Overview",
                "New Features",
                "AI Features",
                "Pricing Changes",
                "Customer Reviews",
                "User Complaints",
            ]
        )
        prompt = load_prompt("feature_compare_agent.md").format(
            competitor=competitor["name"],
            shuttercloud_features="\n".join(f"- {f}" for f in shuttercloud_features()),
            competitor_context=context[:10000],
        )
        analysis = llm.ask(prompt, max_tokens=3000)
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
