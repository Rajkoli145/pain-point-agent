import sys
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.panel import Panel
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from searcher import search_platform, PLATFORMS
from analyzer import analyze_pain_points, save_report

console = Console()

PLATFORM_LABELS = {
    "reddit":       "Reddit (r/subreddit)",
    "hackernews":   "Hacker News",
    "indiehackers": "Indie Hackers",
    "producthunt":  "Product Hunt",
    "quora":        "Quora",
    "twitter":      "Twitter / X",
    "stackoverflow":"Stack Overflow",
}

def main():
    console.print(Panel.fit(
        "[bold]Pain Point Research Agent[/bold]\n"
        "Find real problems people are begging someone to solve",
        border_style="blue"
    ))

    # Platform
    console.print("\n[cyan]Platforms:[/cyan]")
    platform_keys = list(PLATFORMS.keys())
    for i, key in enumerate(platform_keys, 1):
        console.print(f"  {i}. {PLATFORM_LABELS[key]}")

    num_choices = [str(i) for i in range(1, len(platform_keys) + 1)]
    pick = Prompt.ask("[cyan]Pick platform number[/cyan]", choices=num_choices, default="1")
    platform_choice = platform_keys[int(pick) - 1]
    console.print(f"[dim]→ {PLATFORM_LABELS[platform_choice]}[/dim]")

    # Target (subreddit name, topic keyword, etc.)
    if platform_choice == "reddit":
        target = Prompt.ask("[cyan]Subreddit[/cyan] (without r/)", default="Entrepreneur")
        target = target.replace("r/", "").strip()
        label = f"r/{target}"
    else:
        while True:
            target = Prompt.ask("[cyan]Topic / keyword to focus on[/cyan] (e.g. 'invoicing', 'hiring')").strip()
            if target:
                break
            console.print("[red]Topic required for this platform.[/red]")
        label = f"{PLATFORM_LABELS[platform_choice]} — {target}"

    # Mode
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

    limit = IntPrompt.ask("[cyan]How many results to analyze[/cyan]", default=40)

    console.print(f"\n[yellow]Searching {label}...[/yellow]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Fetching results...", total=None)

        posts = search_platform(platform_choice, target, query=query, limit=limit)

        progress.update(task, description=f"Got {len(posts)} results. Analyzing...")

        if not posts:
            console.print("[red]No results found. Try a different platform, topic, or query.[/red]")
            sys.exit(1)

        report = analyze_pain_points(posts, label, context)

        progress.update(task, description="Saving report...")
        filename = save_report(report, platform_choice, target)

    console.print(f"\n[green]Done! Analyzed {len(posts)} results.[/green]")
    console.print(f"[green]Report saved to: {filename}[/green]\n")

    console.print(Markdown(report))

    console.print(f"\n[dim]Full report saved to {filename}[/dim]")


if __name__ == "__main__":
    main()
