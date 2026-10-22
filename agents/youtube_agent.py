"""Pulls recent uploads from a competitor's YouTube channel via the
YouTube Data API v3 (free tier, just needs an API key — no OAuth required
for public channel/search data). Falls back to web search if no key is set.
"""
from __future__ import annotations

import requests

from agents.base_agent import Agent, load_prompt
from utils import llm, web
from utils.config import env


class YouTubeAgent(Agent):
    name = "youtube_agent"

    def run(self, competitor: dict) -> dict[str, str]:
        api_key = env("YOUTUBE_API_KEY")
        channel = competitor.get("youtube")

        if api_key and channel:
            videos = self._fetch_via_api(channel, api_key)
            if videos:
                listing = "\n".join(f"- {v['title']} ({v['publishedAt'][:10]})" for v in videos)
                prompt = load_prompt("youtube_agent.md").format(
                    competitor=competitor["name"], video_list=listing
                )
                return {"YouTube Videos": llm.ask(prompt).strip()}

        try:
            results = web.search(f'{competitor["name"]} site:youtube.com', num=8)
        except web.DataSourceUnavailable:
            return {
                "YouTube Videos": (
                    "_Neither YOUTUBE_API_KEY nor SERPAPI_KEY configured — cannot pull recent videos._"
                )
            }
        if not results:
            return {"YouTube Videos": f"_No recent YouTube results found for {competitor['name']}._"}
        snippets = "\n".join(f"- {r['title']}: {r['snippet']}" for r in results if r.get("snippet"))
        prompt = load_prompt("youtube_agent.md").format(
            competitor=competitor["name"], video_list=snippets
        )
        return {"YouTube Videos": llm.ask(prompt).strip()}

    def _fetch_via_api(self, channel: str, api_key: str) -> list[dict]:
        try:
            search_resp = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "q": channel,
                    "type": "channel",
                    "maxResults": 1,
                    "key": api_key,
                },
                timeout=10,
            )
            search_resp.raise_for_status()
            items = search_resp.json().get("items", [])
            if not items:
                return []
            channel_id = items[0]["snippet"]["channelId"]

            videos_resp = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet",
                    "channelId": channel_id,
                    "order": "date",
                    "maxResults": 10,
                    "type": "video",
                    "key": api_key,
                },
                timeout=10,
            )
            videos_resp.raise_for_status()
            return [
                {"title": v["snippet"]["title"], "publishedAt": v["snippet"]["publishedAt"]}
                for v in videos_resp.json().get("items", [])
            ]
        except requests.RequestException:
            return []
