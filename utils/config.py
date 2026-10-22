"""Loads config.yaml and exposes typed accessors used across all agents."""
from __future__ import annotations

import os
from pathlib import Path
from functools import lru_cache

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


@lru_cache
def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def all_competitors() -> list[dict]:
    """Flatten indian/global/indirect groups into a single list, each tagged with its group."""
    cfg = load_config()
    out = []
    for group, items in cfg["competitors"].items():
        for item in items:
            out.append({**item, "group": group})
    return out


def find_competitor(name: str) -> dict | None:
    for c in all_competitors():
        if c["name"].lower() == name.lower():
            return c
    return None


def shuttercloud_features() -> list[str]:
    return load_config()["company"]["features"]


def slug(name: str) -> str:
    return name.lower().replace(" ", "").replace(".", "").replace("-", "")


def env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)
