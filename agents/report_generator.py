"""Final stage of the pipeline: reads every competitor's freshly-updated
profile and asks Claude/Ollama — acting as the Senior PMM/Competitive Intel
Analyst persona — to synthesize the single Daily Competitor Report in the
exact format ShutterCloud's marketing/product teams expect.

Two-stage synthesis: with 20 competitors, dumping every full profile into
one prompt overwhelms smaller local models (they lose track of competitors
buried in the middle of a long context and start hallucinating). So this
first condenses each group (Indian/Global/Indirect) into a short per-
competitor digest, then synthesizes the final report from those digests
instead of the raw profiles. Also strips placeholder/no-data sections
before condensing so noise ("_No data yet._", "_SERPAPI_KEY not
configured._") doesn't eat context budget for no signal.

Runs once per pipeline execution (not per competitor).
"""
from __future__ import annotations

from datetime import date

from agents.base_agent import load_prompt
from utils import llm
from utils.config import all_competitors, shuttercloud_features
from utils.storage import parse_sections, read_profile, save_daily_report

PLACEHOLDER_PREFIXES = ("_No data yet.", "_SERPAPI_KEY", "_Neither", "_No Ad Library", "_Could not")


def _condensed_profile(name: str) -> str:
    """Drop sections that are just placeholder/no-data notes, keep the rest."""
    sections = parse_sections(read_profile(name))
    kept = []
    for title, body in sections.items():
        if not body or body.strip().startswith(PLACEHOLDER_PREFIXES):
            continue
        kept.append(f"## {title}\n{body}")
    return f"# {name}\n" + "\n\n".join(kept) if kept else f"# {name}\n_No usable data collected today._"


def _group_digest(group_name: str, competitors: list[dict]) -> str:
    profiles_blob = "\n\n---\n\n".join(_condensed_profile(c["name"]) for c in competitors)
    prompt = load_prompt("group_digest.md").format(
        group=group_name, profiles=profiles_blob[:60000], count=len(competitors)
    )
    return llm.ask(prompt, max_tokens=3000)


def generate_daily_report(competitor_names: list[str] | None = None) -> str:
    competitors = all_competitors()
    if competitor_names:
        wanted = {n.lower() for n in competitor_names}
        competitors = [c for c in competitors if c["name"].lower() in wanted]

    groups: dict[str, list[dict]] = {}
    for c in competitors:
        groups.setdefault(c["group"], []).append(c)

    digests = "\n\n".join(
        f"# ===== {group.upper()} COMPETITORS =====\n{_group_digest(group, members)}"
        for group, members in groups.items()
    )

    prompt = load_prompt("report_generator.md").format(
        date=date.today().isoformat(),
        shuttercloud_features="\n".join(f"- {f}" for f in shuttercloud_features()),
        competitor_profiles=digests[:100000],
    )
    report = llm.ask(prompt, max_tokens=8000)
    save_daily_report(report)
    return report
