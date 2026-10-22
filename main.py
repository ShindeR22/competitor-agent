"""Entry point for the ShutterCloud.ai Competitor Research Agent.

Usage:
    python main.py                          # run full daily pipeline, all competitors
    python main.py --competitors FotoOwl,Pixieset
    python main.py --init-only              # just create empty competitor profile files
    python main.py --skip-report            # gather data but don't call the report LLM

Each agent updates its own section(s) of competitors/<slug>.md; the
report_generator then reads all updated profiles and writes
reports/daily/<YYYY-MM-DD>.md.
"""
import argparse
import sys
import traceback

from agents.facebook_agent import FacebookAgent
from agents.feature_compare_agent import FeatureCompareAgent
from agents.instagram_agent import InstagramAgent
from agents.pricing_agent import PricingAgent
from agents.report_generator import generate_daily_report
from agents.reviews_agent import ReviewsAgent
from agents.seo_agent import SEOAgent
from agents.website_agent import WebsiteAgent
from agents.youtube_agent import YouTubeAgent
from utils.config import all_competitors
from utils.storage import init_profile, update_sections

# Order matters: feature_compare_agent must run last since it reads the
# sections every other agent writes.
PIPELINE = [
    WebsiteAgent(),
    PricingAgent(),
    InstagramAgent(),
    FacebookAgent(),
    YouTubeAgent(),
    ReviewsAgent(),
    SEOAgent(),
    FeatureCompareAgent(),
]


def run_competitor(competitor: dict) -> None:
    print(f"\n=== {competitor['name']} ({competitor['group']}) ===")
    init_profile(competitor)
    for agent in PIPELINE:
        try:
            updates = agent.run(competitor)
            update_sections(competitor["name"], competitor, updates)
            print(f"  [{agent.name}] ok — updated: {', '.join(updates.keys())}")
        except Exception as exc:
            print(f"  [{agent.name}] FAILED: {exc}", file=sys.stderr)
            traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="ShutterCloud.ai Competitor Research Agent")
    parser.add_argument("--competitors", help="Comma-separated competitor names (default: all)")
    parser.add_argument("--init-only", action="store_true", help="Only create empty profile files")
    parser.add_argument("--skip-report", action="store_true", help="Skip the final report generation step")
    args = parser.parse_args()

    competitors = all_competitors()
    if args.competitors:
        wanted = {n.strip().lower() for n in args.competitors.split(",")}
        competitors = [c for c in competitors if c["name"].lower() in wanted]
        missing = wanted - {c["name"].lower() for c in competitors}
        if missing:
            print(f"Warning: unknown competitor names ignored: {', '.join(missing)}", file=sys.stderr)

    if args.init_only:
        for c in competitors:
            path = init_profile(c)
            print(f"initialized {path}")
        return

    for c in competitors:
        run_competitor(c)

    if not args.skip_report:
        print("\nGenerating daily report...")
        report_path_names = [c["name"] for c in competitors]
        report = generate_daily_report(report_path_names)
        print(f"Report generated ({len(report)} chars). See reports/daily/.")


if __name__ == "__main__":
    main()
