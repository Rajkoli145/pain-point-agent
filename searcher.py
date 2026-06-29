import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

SERPER_ENDPOINT = "https://google.serper.dev/search"
PAIN_QUERIES = [
    # high-signal complaints
    "I hate that I have to",
    "I hate when",
    "so frustrated",
    "this is a nightmare",
    "waste of time",
    "takes forever",
    "too expensive",
    "pricing is insane",
    "terrible UX",
    "bugs every day",
    "broken",
    "impossible",
    # wishlist
    "wish there was a tool",
    "I wish someone built",
    "why is there no app for",
    "why is there no solution for",
    "there has to be a better way",
    "nobody has solved this",
    "need a tool for",
    "looking for software",
    "any software for",
    "alternative to",
    # manual work signals
    "manually every time",
    "still doing manually",
    "copy paste every day",
    "repetitive task",
    "takes hours",
    "daily workflow",
    "manual process",
    "spreadsheet hell",
    "Excel workaround",
    "currently using Google Sheets",
    "Notion template",
    "Zapier workflow",
    "Python script just to",
    # jobs to be done
    "how do you currently",
    "how do you manage",
    "how do you track",
    "how do you automate",
    "anyone else struggle with",
    "what is the hardest part of",
    # workarounds = SaaS gap
    "Excel template",
    "CSV workaround",
    "feature request",
    "missing feature",
    # validation
    "what software do you use for",
    "tool recommendations",
    "what are you paying for",
]

BATCH_QUERIES = [
    "I hate that I have to",
    "wish there was a tool",
    "why is there no",
    "manually every time",
    "there has to be a better way",
    "spreadsheet hell",
    "takes hours just to",
    "I wish someone built",
    "anyone else struggle with",
    "currently using Google Sheets",
]

PLATFORMS = {
    "reddit":       "reddit r/{target}",
    "hackernews":   "hacker news ycombinator {target}",
    "indiehackers": "indiehackers {target}",
    "producthunt":  "producthunt {target}",
    "quora":        "quora {target}",
    "twitter":      "twitter {target}",
    "stackoverflow":"stackoverflow {target}",
}


def _search(query: str, retries: int = 3) -> list:
    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json",
    }
    for attempt in range(retries):
        try:
            resp = requests.post(SERPER_ENDPOINT, headers=headers, json={"q": query, "num": 20}, timeout=15)
            if not resp.ok:
                raise RuntimeError(f"Serper {resp.status_code}: {resp.text[:300]}")
            time.sleep(1.2)  # stay under free tier rate limit
            return resp.json().get("organic", [])
        except (requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
            else:
                raise RuntimeError(f"Connection failed after {retries} attempts: {e}")
    return []


def _extract(result: dict) -> dict:
    return {
        "title": result.get("title", ""),
        "body": result.get("snippet", ""),
        "url": result.get("link", ""),
        "date": result.get("date", "unknown date"),
        "score": 0,
        "comments": [],
        "flair": "",
    }


def _build_query(platform: str, target: str, pain: str) -> str:
    template = PLATFORMS.get(platform, "reddit r/{target}")
    base = template.format(target=target)
    return f"{base} {pain}"


def search_platform(platform: str, target: str, query: str = "", limit: int = 30, query_set: list = None) -> list:
    pool = query_set if query_set is not None else PAIN_QUERIES
    queries = []
    if query:
        queries.append(_build_query(platform, target, query))
    for pq in pool:
        queries.append(_build_query(platform, target, pq))

    # run ALL queries, collect everything, then cap at limit
    seen = set()
    posts = []
    for q in queries:
        for result in _search(q):
            url = result.get("link", "")
            if url and url not in seen:
                seen.add(url)
                posts.append(_extract(result))

    return posts[:limit]


# kept for backward compat
def search_subreddit(subreddit_name: str, query: str = "", limit: int = 30) -> list:
    return search_platform("reddit", subreddit_name, query=query, limit=limit)


def scrape_subreddit(subreddit_name: str, limit: int = 50, sort: str = "hot") -> list:
    return search_platform("reddit", subreddit_name, limit=limit)
