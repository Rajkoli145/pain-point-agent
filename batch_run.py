"""
Overnight batch scraper — runs 50+ communities, saves reports to output/<platform>/
Uses BATCH_QUERIES (10 queries) to stay within Serper free tier (500 calls/run).
"""
import os
import sys
import time
import traceback
from searcher import search_platform, BATCH_QUERIES
from analyzer import analyze_pain_points, save_report

TARGETS = [
    # (platform, target/topic)

    # Reddit — 25 subreddits
    ("reddit", "Entrepreneur"),
    ("reddit", "smallbusiness"),
    ("reddit", "SaaS"),
    ("reddit", "webdev"),
    ("reddit", "freelance"),
    ("reddit", "marketing"),
    ("reddit", "ecommerce"),
    ("reddit", "startups"),
    ("reddit", "programming"),
    ("reddit", "datascience"),
    ("reddit", "MachineLearning"),
    ("reddit", "recruiting"),
    ("reddit", "Accounting"),
    ("reddit", "legaladvice"),
    ("reddit", "RealEstate"),
    ("reddit", "personalfinance"),
    ("reddit", "aws"),
    ("reddit", "devops"),
    ("reddit", "ProductManagement"),
    ("reddit", "sales"),
    ("reddit", "CustomerSuccess"),
    ("reddit", "nocode"),
    ("reddit", "Automate"),
    ("reddit", "msp"),
    ("reddit", "consulting"),

    # Hacker News — 8 topics
    ("hackernews", "saas"),
    ("hackernews", "automation"),
    ("hackernews", "productivity"),
    ("hackernews", "developer tools"),
    ("hackernews", "remote work"),
    ("hackernews", "hiring"),
    ("hackernews", "b2b software"),
    ("hackernews", "pricing"),

    # Indie Hackers — 7 topics
    ("indiehackers", "saas"),
    ("indiehackers", "automation"),
    ("indiehackers", "marketing"),
    ("indiehackers", "growth"),
    ("indiehackers", "pricing"),
    ("indiehackers", "tools"),
    ("indiehackers", "workflow"),

    # Quora — 5 topics
    ("quora", "business software"),
    ("quora", "workflow automation"),
    ("quora", "startup tools"),
    ("quora", "small business"),
    ("quora", "freelancing"),

    # Product Hunt — 5 topics
    ("producthunt", "productivity"),
    ("producthunt", "automation"),
    ("producthunt", "saas"),
    ("producthunt", "developer tools"),
    ("producthunt", "business"),
]

LIMIT_PER_TARGET = 40


def run():
    total = len(TARGETS)
    passed = 0
    failed = []

    print(f"\n=== Batch run: {total} communities, 10 queries each ===")
    print(f"Estimated Serper calls: {total * 10} / 2500 monthly quota\n")

    for i, (platform, target) in enumerate(TARGETS, 1):
        label = f"[{i}/{total}] {platform} — {target}"
        print(f"{label} ... ", end="", flush=True)

        try:
            posts = search_platform(
                platform, target,
                limit=LIMIT_PER_TARGET,
                query_set=BATCH_QUERIES
            )

            if not posts:
                print("0 results, skipping")
                continue

            report = analyze_pain_points(posts, f"{platform}/{target}", context="")
            filename = save_report(report, platform, target)
            print(f"done — {len(posts)} results → {filename}")
            passed += 1

        except Exception as e:
            print(f"FAILED: {e}")
            failed.append((label, str(e)))
            traceback.print_exc()

        # breathing room between communities
        time.sleep(2)

    print(f"\n=== Done: {passed}/{total} succeeded ===")
    if failed:
        print("Failed:")
        for label, err in failed:
            print(f"  {label}: {err}")


if __name__ == "__main__":
    run()
