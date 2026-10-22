"""Common interface every agent implements.

Each agent's `run(competitor)` returns a dict of {profile_section_name: markdown_body}
which the orchestrator merges into competitors/<slug>.md via utils.storage.update_sections.
Agents should never raise on missing optional data sources — they should
note the gap in the returned markdown (e.g. "_No SERPAPI_KEY configured._")
so the report generator can see the gap too.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from utils.config import ROOT

PROMPTS_DIR = ROOT / "prompts"


def load_prompt(filename: str) -> str:
    return (PROMPTS_DIR / filename).read_text()


class Agent(ABC):
    name: str = "base_agent"

    @abstractmethod
    def run(self, competitor: dict) -> dict[str, str]:
        """Gather data for one competitor and return {section_name: markdown_body}."""
        raise NotImplementedError
