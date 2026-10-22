"""Read/write helpers for competitor profile markdown files, raw snapshots
(used for change detection), and generated reports.

Each competitor has one file at competitors/<slug>.md with a fixed set of
H2 sections (see SECTIONS below). Agents update individual sections without
touching the rest of the file, so the profile accumulates history-aware
context run over run instead of being clobbered daily.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

from utils.config import ROOT, slug

COMPETITORS_DIR = ROOT / "competitors"
SNAPSHOTS_DIR = ROOT / "data" / "snapshots"
REPORTS_DAILY = ROOT / "reports" / "daily"
REPORTS_WEEKLY = ROOT / "reports" / "weekly"

SECTIONS = [
    "Company Overview",
    "Latest Product Updates",
    "New Features",
    "AI Features",
    "Pricing Changes",
    "Website Changes",
    "Landing Pages",
    "Blogs",
    "Instagram Posts & Reels",
    "Facebook Posts",
    "YouTube Videos",
    "Running Ads",
    "App Updates",
    "Customer Reviews",
    "User Complaints",
    "User Likes",
    "SEO Keywords",
    "Feature Comparison with ShutterCloud",
    "Strengths",
    "Weaknesses",
]


def profile_path(name: str) -> Path:
    return COMPETITORS_DIR / f"{slug(name)}.md"


def init_profile(competitor: dict) -> Path:
    """Create a competitor markdown file with empty sections if it doesn't exist yet."""
    path = profile_path(competitor["name"])
    if path.exists():
        return path
    lines = [
        f"# {competitor['name']}",
        "",
        f"- **Website:** {competitor.get('website', 'n/a')}",
        f"- **Group:** {competitor.get('group', 'n/a')}",
        f"- **Last updated:** never",
        "",
    ]
    for section in SECTIONS:
        lines += [f"## {section}", "", "_No data yet._", ""]
    path.write_text("\n".join(lines))
    return path


def read_profile(name: str) -> str:
    path = profile_path(name)
    return path.read_text() if path.exists() else ""


def parse_sections(markdown: str) -> dict[str, str]:
    """Split a profile file into {section_title: body}."""
    parts = re.split(r"^## (.+)$", markdown, flags=re.MULTILINE)
    result = {}
    # parts[0] is the preamble before the first "## "; then alternating title/body
    for i in range(1, len(parts), 2):
        title = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        result[title] = body
    return result


def update_sections(name: str, competitor: dict, updates: dict[str, str]) -> None:
    """Overwrite the given sections of a competitor's profile, leave the rest untouched."""
    path = init_profile(competitor)
    markdown = path.read_text()
    sections = parse_sections(markdown)
    sections.update({k: v for k, v in updates.items() if v})

    lines = [
        f"# {competitor['name']}",
        "",
        f"- **Website:** {competitor.get('website', 'n/a')}",
        f"- **Group:** {competitor.get('group', 'n/a')}",
        f"- **Last updated:** {datetime.now().isoformat(timespec='minutes')}",
        "",
    ]
    for section in SECTIONS:
        body = sections.get(section, "").strip() or "_No data yet._"
        lines += [f"## {section}", "", body, ""]
    path.write_text("\n".join(lines))


def load_previous_snapshot(name: str, source: str) -> str | None:
    path = SNAPSHOTS_DIR / f"{slug(name)}__{source}.txt"
    return path.read_text() if path.exists() else None


def save_snapshot(name: str, source: str, content: str) -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOTS_DIR / f"{slug(name)}__{source}.txt"
    path.write_text(content)


def save_json_snapshot(name: str, source: str, data: dict) -> None:
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOTS_DIR / f"{slug(name)}__{source}.json"
    path.write_text(json.dumps(data, indent=2))


def load_json_snapshot(name: str, source: str) -> dict | None:
    path = SNAPSHOTS_DIR / f"{slug(name)}__{source}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_daily_report(content: str, day: date | None = None) -> Path:
    day = day or date.today()
    REPORTS_DAILY.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DAILY / f"{day.isoformat()}.md"
    path.write_text(content)
    return path


def save_weekly_report(content: str, week_label: str | None = None) -> Path:
    week_label = week_label or f"{date.today().isocalendar().year}-W{date.today().isocalendar().week:02d}"
    REPORTS_WEEKLY.mkdir(parents=True, exist_ok=True)
    path = REPORTS_WEEKLY / f"{week_label}.md"
    path.write_text(content)
    return path
