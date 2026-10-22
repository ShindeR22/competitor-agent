"""LLM wrapper. Defaults to a local Ollama model (free, no API key, runs on
your machine) so agents don't repeat HTTP boilerplate. Set llm.provider to
"anthropic" in config.yaml if you'd rather use Claude via ANTHROPIC_API_KEY,
or "gemini" to use Google's free-tier Gemini API via GEMINI_API_KEY.
"""
from __future__ import annotations

import re
import time

import requests

from utils.config import env, load_config

OLLAMA_URL = "http://localhost:11434/api/chat"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def ask(prompt: str, system: str | None = None, max_tokens: int | None = None) -> str:
    """Send a single-turn prompt to the configured LLM and return the text response."""
    cfg = load_config()["llm"]
    provider = cfg.get("provider", "ollama")
    if provider == "anthropic":
        return _ask_anthropic(prompt, system, max_tokens, cfg)
    if provider == "gemini":
        return _ask_gemini(prompt, system, max_tokens, cfg)
    return _ask_ollama(prompt, system, cfg)


def _ask_ollama(prompt: str, system: str | None, cfg: dict) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": cfg["model"],
                "messages": messages,
                "stream": False,
                "options": {"num_ctx": cfg.get("num_ctx", 16384)},
            },
            timeout=300,
        )
        resp.raise_for_status()
    except requests.ConnectionError as exc:
        raise RuntimeError(
            "Could not reach Ollama at http://localhost:11434. "
            "Is it running? Try: brew services start ollama"
        ) from exc
    return resp.json()["message"]["content"]


def _ask_anthropic(prompt: str, system: str | None, max_tokens: int | None, cfg: dict) -> str:
    from anthropic import Anthropic

    api_key = env("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in.")
    kwargs = {
        "model": cfg["model"],
        "max_tokens": max_tokens or cfg.get("max_tokens", 4096),
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system
    resp = Anthropic(api_key=api_key).messages.create(**kwargs)
    return "".join(block.text for block in resp.content if block.type == "text")


def _ask_gemini(prompt: str, system: str | None, max_tokens: int | None, cfg: dict) -> str:
    api_key = env("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey "
            "and add it to .env."
        )
    model = cfg.get("model", "gemini-2.0-flash")
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens or cfg.get("max_tokens", 4096)},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}

    url = GEMINI_URL.format(model=model)
    max_retries = 5
    for attempt in range(max_retries):
        resp = requests.post(url, params={"key": api_key}, json=body, timeout=300)
        if resp.status_code != 429:
            break
        delay = _retry_delay_seconds(resp.text, default=15)
        time.sleep(delay)
    resp.raise_for_status()
    data = resp.json()
    parts = data["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts)


def _retry_delay_seconds(error_body: str, default: int) -> float:
    match = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', error_body)
    return float(match.group(1)) + 1 if match else default
