# ShutterCloud.ai Competitor Research Agent

Daily competitor intelligence pipeline for ShutterCloud.ai's marketing and
product teams. Monitors 20 competitors (Indian, global, indirect) across
product, pricing, website, social, reviews, and SEO, then synthesizes a
single actionable Daily Competitor Report.

## Architecture

Modular by design — each data source is its own agent, each competitor gets
its own persistent markdown profile, and the report generator is a separate
final synthesis step. Nothing is a monolithic script.

```
competitor-agent/
├── agents/                  # one module per data source
│   ├── base_agent.py        # shared Agent interface
│   ├── website_agent.py     # site crawl + diff → overview, updates, features, AI, blogs, landing pages
│   ├── pricing_agent.py     # pricing page diff → pricing changes
│   ├── instagram_agent.py   # IG posts/Reels via search
│   ├── facebook_agent.py    # FB posts + Meta Ad Library signal
│   ├── youtube_agent.py     # YouTube Data API / search fallback
│   ├── reviews_agent.py     # G2/Capterra/Trustpilot/app stores → reviews, complaints, likes
│   ├── seo_agent.py         # on-page SEO signal
│   ├── feature_compare_agent.py  # feature table + strengths/weaknesses vs ShutterCloud
│   └── report_generator.py  # final synthesis → Daily Competitor Report
├── competitors/              # one persistent .md profile per competitor (20 sections each)
├── prompts/                  # every agent's prompt lives here, not hardcoded in code
├── reports/
│   ├── daily/                # YYYY-MM-DD.md, one per run
│   └── weekly/
├── data/snapshots/           # raw page snapshots, used to diff "what changed today"
├── config.yaml                # competitor list + ShutterCloud feature set — edit here, not in code
└── main.py                    # orchestrator
```

## Setup

```bash
cd competitor-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# then fill in .env — see "Data sources" below
```

### LLM: local + free by default

This project uses [Ollama](https://ollama.com) by default — a free, local
LLM runtime, no API key or billing needed.

```bash
brew install ollama
brew services start ollama
ollama pull llama3.1:8b
```

That's it — `config.yaml` already has `llm.provider: ollama` and
`llm.model: llama3.1:8b`. No `.env` entry required for this path.

Note: with the *full* 20-competitor daily report (all profiles concatenated
into one synthesis prompt), even 8b-class local models can lose track of
competitors buried in the middle of a very long prompt — a known small-model
limitation, not a bug. If report quality still misses competitors at that
scale, either run `report_generator.generate_daily_report()` per competitor
group instead of all-at-once, or switch to `llm.provider: anthropic`.

Tighter on bandwidth/RAM? `ollama pull llama3.2:3b` and set `llm.model:
llama3.2:3b` instead — faster, smaller, but noticeably weaker at synthesizing
long multi-competitor reports (fine for single-competitor testing).

If you'd rather use Claude (faster, higher-quality synthesis, small per-call
cost), set `llm.provider: anthropic` and `llm.model: claude-sonnet-5` in
`config.yaml`, `pip install anthropic`, and set `ANTHROPIC_API_KEY` in `.env`.

Optional data-source keys (independent of which LLM you use):
`SERPAPI_KEY` (Instagram/Facebook/YouTube/reviews/ads all degrade to "no data
source configured" without it), `YOUTUBE_API_KEY` (better YouTube data than
search), `META_GRAPH_API_TOKEN` / `FACEBOOK_AD_LIBRARY_TOKEN` (for owned-page
or Ad Library API access).

## Run

```bash
python main.py                                  # full run, all 20 competitors
python main.py --competitors FotoOwl,Pixieset    # just a subset
python main.py --init-only                       # create empty profiles only, no API calls
python main.py --skip-report                     # gather data, skip the final report LLM call
```

Output:
- `competitors/<slug>.md` — updated in place, section by section, every run.
- `reports/daily/<date>.md` — the Daily Competitor Report in the required format.

## How it works

1. `main.py` loads the competitor list from `config.yaml`.
2. For each competitor, every agent in the pipeline runs in sequence and
   returns `{profile_section: markdown}`. `utils.storage.update_sections`
   merges that into the competitor's `.md` file, leaving other sections
   untouched — so profiles accumulate context rather than being wiped daily.
3. `website_agent` and `pricing_agent` diff today's scrape against
   `data/snapshots/` so the report only flags real changes, not a
   re-summary of static content.
4. `feature_compare_agent` runs last per competitor — it reads everything
   the other agents just wrote and produces the feature table +
   strengths/weaknesses.
5. `report_generator` runs once at the end, reads every updated profile,
   and asks Claude (as the Senior PMM/Competitive Intel Analyst persona) to
   synthesize the single Daily Competitor Report — comparisons, "why it
   matters," concrete actions, scores, priorities — per the rules in
   `prompts/report_generator.md`.

## Extending

- **Add a competitor:** add an entry to `config.yaml` under the right group,
  then `python main.py --init-only` to create its profile file.
- **Add a data source:** create `agents/your_agent.py` implementing
  `Agent.run(competitor) -> dict[str, str]`, add a prompt in `prompts/`, and
  register it in `PIPELINE` in `main.py`.
- **Change ShutterCloud's feature set:** edit `company.features` in
  `config.yaml` — it flows automatically into feature comparison and the
  final report.
- **Wire in a real API** (Meta Graph, YouTube Data, Ad Library, Ahrefs/
  SEMrush): each agent already isolates its data-fetch behind a small
  method/function — replace the search-based fallback there without
  touching prompts or the orchestrator.

## Scheduling

For a daily cron run:

```
0 7 * * * cd /path/to/competitor-agent && .venv/bin/python main.py >> logs/run.log 2>&1
```
