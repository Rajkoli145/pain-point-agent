from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()

def _get_groq_keys() -> list:
    keys = []
    for i in range(1, 10):
        k = os.getenv(f"GROQ_API_KEY_{i}")
        if k:
            keys.append(k)
    if not keys:
        k = os.getenv("GROQ_API_KEY")
        if k:
            keys.append(k)
    return keys

def format_posts_for_claude(posts: list) -> str:
    """Convert scraped posts into a clean text block for the LLM."""
    formatted = []
    for i, post in enumerate(posts, 1):
        post_text = f"""
--- POST {i} ---
Title: {post['title']}
Date: {post.get('date', 'unknown')}
Body: {post['body'][:300]}
URL: {post['url']}
"""
        if post['comments']:
            post_text += "Top Comments:\n"
            for j, comment in enumerate(post['comments'], 1):
                post_text += f"  Comment {j} (score: {comment['score']}): {comment['text']}\n"

        formatted.append(post_text)

    return "\n".join(formatted)


def analyze_pain_points(posts: list, subreddit: str, context: str = "") -> str:
    """
    Send posts to Claude and get back a structured pain point analysis.
    Returns markdown report as string.
    """
    groq_keys = _get_groq_keys()
    if not groq_keys:
        raise RuntimeError("No GROQ_API_KEY found in .env")

    # Groq free tier: 12000 TPM — cap at 80 posts (~300 chars each stays safe)
    if len(posts) > 80:
        posts = posts[:80]

    posts_text = format_posts_for_claude(posts)

    prompt = f"""You are a product researcher analyzing Reddit posts from r/{subreddit} to find real user pain points and potential SaaS opportunities.

{f'Context/Focus: {context}' if context else ''}

Here are {len(posts)} Reddit posts with their comments:

{posts_text}

Analyze all of this and produce a structured research report in markdown with these exact sections:

# Reddit Pain Point Research — r/{subreddit}

## Top Pain Points
List the 5-8 most frequently mentioned frustrations. For each:
- **Pain point name** (1 line description)
- Frequency: how many posts/comments mention this
- Severity: Low / Medium / High (based on emotion in language)
- Verbatim quote: the most powerful exact phrase someone used
- Example post: link to the best example

## Exact Customer Language
30-40 verbatim phrases and sentences people actually used.
These are gold for ad copy and landing pages.
Format as a simple bulleted list of quotes.

## Patterns & Triggers
What situations cause these complaints?
What are people trying to do when they hit these problems?
What have they already tried that didn't work?

## Objections & Blockers
What stops people from solving this themselves?
What solutions did they try and why did those fail?

## Potential SaaS Ideas
Based purely on what people are begging for in these posts,
list 5-8 specific software ideas that would directly solve these complaints.
For each idea:
- **Idea name**
- Problem it solves (in the user's own language)
- Who pays for it
- Rough willingness to pay signal from the posts
- Difficulty: Easy / Medium / Hard to build

## Biggest Opportunity
In 2-3 sentences, what is the single highest-signal opportunity you found?
Which pain point is most frequent, most severe, and least served by existing tools?

Be specific. Use real quotes from the posts. Don't generalize."""

    for i, key in enumerate(groq_keys):
        try:
            client = Groq(api_key=key)
            message = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.choices[0].message.content
        except Exception as e:
            if "rate_limit" in str(e).lower() or "413" in str(e) or "429" in str(e):
                print(f"  [groq] key {i+1} rate limited, rotating...")
                continue
            raise

    raise RuntimeError("All Groq API keys exhausted / rate limited")


def save_report(report: str, platform: str, target: str = "") -> str:
    """Save the report to output/<platform>/ folder."""
    from datetime import datetime

    folder = f"output/{platform}"
    os.makedirs(folder, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    slug = target.replace(" ", "_") if target else "general"
    filename = f"{folder}/{slug}_{timestamp}.md"

    with open(filename, "w") as f:
        f.write(report)

    return filename
