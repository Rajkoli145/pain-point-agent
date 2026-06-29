# Reddit Pain Point Research Agent

## What this does
Scrapes Reddit for real user complaints in a subreddit,
feeds all posts + comments to Claude, and outputs a clean
markdown report of: top pain points, exact user phrases,
and potential SaaS ideas hiding in the complaints.

## Stack
- Python 3.11+
- PRAW (Reddit API wrapper) — `pip install praw`
- Anthropic Python SDK — `pip install anthropic`
- Rich (pretty terminal output) — `pip install rich`
- python-dotenv — `pip install python-dotenv`

## File structure
```
reddit-agent/
├── .env
├── main.py
├── reddit_scraper.py
├── analyzer.py
└── output/
    └── (reports saved here as .md files)
```

## .env file
```
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=RedditResearchAgent/1.0
ANTHROPIC_API_KEY=your_anthropic_key
```

## reddit_scraper.py
```python
import praw
import os
from dotenv import load_dotenv

load_dotenv()

def get_reddit_client():
    return praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT")
    )

def scrape_subreddit(subreddit_name: str, limit: int = 50, sort: str = "hot"):
    """
    Scrape posts + top comments from a subreddit.
    sort options: hot, new, top, rising
    Returns list of dicts with post data.
    """
    reddit = get_reddit_client()
    subreddit = reddit.subreddit(subreddit_name)
    
    posts = []
    
    if sort == "hot":
        submissions = subreddit.hot(limit=limit)
    elif sort == "top":
        submissions = subreddit.top(limit=limit, time_filter="month")
    elif sort == "new":
        submissions = subreddit.new(limit=limit)
    else:
        submissions = subreddit.hot(limit=limit)
    
    for submission in submissions:
        # Skip if no text content
        if not submission.selftext or submission.selftext == "[removed]":
            continue
            
        # Get top 10 comments
        submission.comments.replace_more(limit=0)
        top_comments = []
        for comment in submission.comments.list()[:10]:
            if hasattr(comment, 'body') and comment.body != "[removed]":
                top_comments.append({
                    "text": comment.body[:500],  # cap at 500 chars
                    "score": comment.score
                })
        
        posts.append({
            "title": submission.title,
            "body": submission.selftext[:1000],  # cap at 1000 chars
            "score": submission.score,
            "url": f"https://reddit.com{submission.permalink}",
            "comments": top_comments,
            "flair": submission.link_flair_text or ""
        })
    
    return posts


def search_subreddit(subreddit_name: str, query: str, limit: int = 30):
    """
    Search a subreddit for specific query.
    Good for finding complaints about a specific topic.
    """
    reddit = get_reddit_client()
    subreddit = reddit.subreddit(subreddit_name)
    
    posts = []
    for submission in subreddit.search(query, limit=limit, sort="relevance"):
        if not submission.selftext or submission.selftext == "[removed]":
            continue
            
        submission.comments.replace_more(limit=0)
        top_comments = []
        for comment in submission.comments.list()[:8]:
            if hasattr(comment, 'body') and comment.body != "[removed]":
                top_comments.append({
                    "text": comment.body[:500],
                    "score": comment.score
                })
        
        posts.append({
            "title": submission.title,
            "body": submission.selftext[:1000],
            "score": submission.score,
            "url": f"https://reddit.com{submission.permalink}",
            "comments": top_comments,
            "flair": submission.link_flair_text or ""
        })
    
    return posts
```

## analyzer.py
```python
import anthropic
import os
import json
from dotenv import load_dotenv

load_dotenv()

def format_posts_for_claude(posts: list) -> str:
    """Convert scraped posts into a clean text block for Claude."""
    formatted = []
    for i, post in enumerate(posts, 1):
        post_text = f"""
--- POST {i} ---
Title: {post['title']}
Body: {post['body']}
Score: {post['score']}
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
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
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

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    
    return message.content[0].text


def save_report(report: str, subreddit: str, query: str = ""):
    """Save the report to output folder."""
    import os
    from datetime import datetime
    
    os.makedirs("output", exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"output/{subreddit}_{query.replace(' ', '_') if query else 'general'}_{timestamp}.md"
    
    with open(filename, "w") as f:
        f.write(report)
    
    return filename
```

## main.py
```python
import sys
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from reddit_scraper import scrape_subreddit, search_subreddit
from analyzer import analyze_pain_points, save_report

console = Console()

def main():
    console.print(Panel.fit(
        "[bold]Reddit Pain Point Research Agent[/bold]\n"
        "Find real problems people are begging someone to solve",
        border_style="blue"
    ))
    
    # Get subreddit
    subreddit = Prompt.ask("\n[cyan]Subreddit to research[/cyan]", 
                           default="SaaS")
    subreddit = subreddit.replace("r/", "").strip()
    
    # Get mode
    mode = Prompt.ask(
        "[cyan]Mode[/cyan]",
        choices=["browse", "search"],
        default="browse"
    )
    
    query = ""
    context = ""
    
    if mode == "search":
        query = Prompt.ask("[cyan]Search query[/cyan] (e.g. 'frustrated annoying broken')")
        context = f"Focus on complaints about: {query}"
    else:
        context = Prompt.ask(
            "[cyan]Optional focus[/cyan] (press enter to skip)",
            default=""
        )
    
    limit = IntPrompt.ask("[cyan]How many posts to analyze[/cyan]", default=40)
    
    # Scrape
    console.print(f"\n[yellow]Scraping r/{subreddit}...[/yellow]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Fetching posts and comments...", total=None)
        
        if mode == "search":
            posts = search_subreddit(subreddit, query, limit=limit)
        else:
            posts = scrape_subreddit(subreddit, limit=limit, sort="hot")
        
        progress.update(task, description=f"Got {len(posts)} posts. Sending to Claude...")
        
        if not posts:
            console.print("[red]No posts found. Try a different subreddit or query.[/red]")
            sys.exit(1)
        
        report = analyze_pain_points(posts, subreddit, context)
        
        progress.update(task, description="Saving report...")
        filename = save_report(report, subreddit, query)
    
    # Show results
    console.print(f"\n[green]Done! Analyzed {len(posts)} posts.[/green]")
    console.print(f"[green]Report saved to: {filename}[/green]\n")
    
    # Print report to terminal
    console.print(Markdown(report))
    
    console.print(f"\n[dim]Full report saved to {filename}[/dim]")


if __name__ == "__main__":
    main()
```

## How to get Reddit API credentials (free, 2 mins)
1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app" at the bottom
3. Name: RedditResearchAgent
4. Type: script
5. Redirect URI: http://localhost:8080
6. Click create
7. Copy the client_id (under the app name) and client_secret
8. Paste into .env file

## How to run
```bash
# Install deps
pip install praw anthropic rich python-dotenv

# Run
python main.py
```

## Example usage for finding SaaS ideas
Run it on these subreddits one by one:

1. r/SaaS — search "frustrated" or "wish there was"
2. r/webdev — search "annoying" or "waste of time"  
3. r/freelance — search "problem" or "hate"
4. r/indiehackers — browse hot (people share real pain)
5. r/startups — search "tool" or "broken"
6. r/cscareerquestions — browse hot
7. r/entrepreneur — search "wish" or "nobody solves"

## Pro tip searches that find gold
- "why is there no tool that"
- "I hate that I have to"
- "wish someone would build"
- "manually every time"
- "so frustrating"
- "hours just to"
- "there has to be a better way"
