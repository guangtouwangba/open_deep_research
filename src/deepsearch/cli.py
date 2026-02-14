"""CLI interface for DeepSearch."""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from deepsearch.config import Config
from deepsearch.output.formatters import format_findings_table, format_progress
from deepsearch.output.report import ReportGenerator
from deepsearch.search import OpenRouterSearch, TavilySearch
from deepsearch.state import ResearchDepth, ResearchState, ResearchStatus
from deepsearch.storage import Storage
from deepsearch.workflow import create_llm, create_research_workflow

console = Console()

# Global flag for graceful shutdown
should_stop = False


def signal_handler(sig, frame):
    """Handle interrupt signal."""
    global should_stop
    should_stop = True
    console.print("\n[yellow]⚠️  Interrupted by user. Saving state...[/yellow]")


signal.signal(signal.SIGINT, signal_handler)


class DefaultGroup(click.Group):
    """Custom Click Group that routes unknown commands to 'run'."""

    def parse_args(self, ctx, args):
        # If the first arg is not a known subcommand, assume it's a topic for 'run'
        if args and args[0] not in self.commands and not args[0].startswith("-"):
            args = ["run"] + args
        return super().parse_args(ctx, args)


@click.group(cls=DefaultGroup)
@click.version_option(version="0.1.0", prog_name="deepsearch")
def main():
    """DeepSearch CLI - Deep research powered by LangGraph.

    \b
    Quick usage:
      ds "your research topic"
      ds "topic" --deep
      ds "topic" --depth comprehensive --output report.md
    """
    pass


@main.command()
@click.argument("topic")
@click.option(
    "--depth",
    "-d",
    type=click.Choice(["quick", "balanced", "comprehensive"]),
    default="balanced",
    help="Research depth level",
)
@click.option(
    "--deep",
    is_flag=True,
    default=False,
    help="Shortcut for --depth comprehensive",
)
@click.option(
    "--search",
    "-s",
    type=click.Choice(["openrouter", "tavily"]),
    help="Search provider",
)
@click.option(
    "--max-iterations",
    "-i",
    type=int,
    help="Maximum research iterations",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path",
)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "json"]),
    default="markdown",
    help="Output format",
)
def run(
    topic: str,
    depth: str,
    deep: bool,
    search: Optional[str],
    max_iterations: Optional[int],
    output: Optional[Path],
    format: str,
):
    """Run a new research task."""
    if deep:
        depth = "comprehensive"
    asyncio.run(_run_research(topic, depth, search, max_iterations, output, format))


async def _run_research(
    topic: str,
    depth: str,
    search_provider: Optional[str],
    max_iterations: Optional[int],
    output_path: Optional[Path],
    output_format: str,
):
    """Execute research workflow."""
    # Load config
    config = Config.load()

    # Validate API keys
    search_api_key = config.get_search_api_key()
    llm_api_key = config.get_llm_api_key()

    if not search_api_key:
        console.print("[red]Error: Search API key not configured[/red]")
        console.print("Set OPENROUTER_API_KEY or TAVILY_API_KEY environment variable")
        sys.exit(1)

    if not llm_api_key:
        console.print("[red]Error: LLM API key not configured[/red]")
        console.exit(1)

    # Initialize components
    storage = Storage(config.storage.get_db_path())
    await storage.init()

    # Create search tool
    provider = search_provider or config.search.provider
    if provider == "openrouter":
        search_tool = OpenRouterSearch(
            api_key=search_api_key,
            model=config.search.model,
            verbose=True,
        )
    elif provider == "tavily":
        search_tool = TavilySearch(search_api_key, verbose=True)
    else:
        console.print(f"[red]Unknown search provider: {provider}[/red]")
        sys.exit(1)

    # Create LLM
    llm = create_llm({
        "provider": config.llm.provider,
        "model": config.llm.model,
        "api_key": llm_api_key,
    })

    # Create workflow
    workflow = create_research_workflow(llm, search_tool)

    # Create job
    job_id = await storage.create_job(
        topic=topic,
        depth=depth,
        max_iterations=max_iterations or config.defaults.max_iterations,
    )

    console.print(f"[green]🚀 Starting research: {topic}[/green]")
    console.print(f"[dim]Job ID: {job_id}[/dim]\n")

    # Initial state
    state = ResearchState(
        job_id=job_id,
        topic=topic,
        depth=ResearchDepth(depth),
        status=ResearchStatus.PENDING,
        plan=[],
        current_question_index=0,
        findings=[],
        search_history=[],
        iteration=0,
        max_iterations=max_iterations or config.defaults.max_iterations,
        reflection=None,
        verified_findings=[],
        conflicts=[],
        report="",
        report_sections=[],
        error=None,
    )

    # Progress tracking (no Live display to allow log output)
    try:
        last_node = None
        # Execute workflow
        async for event in workflow.astream(state):
            if should_stop:
                state["status"] = ResearchStatus.PAUSED
                await storage.save_state(state)
                console.print(f"\n[yellow]⏸️  Research paused. Resume with:[/yellow]")
                console.print(f"   deepsearch continue --id {job_id}")
                return

            # LangGraph astream returns {node_name: state_update}
            # Merge the update into our state
            if isinstance(event, dict):
                for node_name, node_output in event.items():
                    # Log node transitions
                    if node_name != last_node:
                        node_icons = {
                            "plan": "📋 Planning research questions...",
                            "research": "🔬 Researching...",
                            "reflect": "🤔 Reflecting on findings...",
                            "verify": "✅ Verifying findings...",
                            "write": "📝 Writing report...",
                        }
                        if node_name in node_icons:
                            console.print(f"\n[bold cyan]{node_icons[node_name]}[/bold cyan]")
                        last_node = node_name

                    if isinstance(node_output, dict):
                        # Merge node output into state
                        for key, value in node_output.items():
                            state[key] = value

                        # Log specific updates
                        if node_name == "plan" and "plan" in node_output:
                            plan = node_output["plan"]
                            console.print(f"[green]   Generated {len(plan)} research questions[/green]")
                            for i, q in enumerate(plan[:5], 1):
                                q_text = q.question if hasattr(q, 'question') else q.get('question', str(q))
                                console.print(f"[dim]   {i}. {q_text[:60]}...[/dim]")

                        if node_name == "reflect" and "reflection" in node_output:
                            ref = node_output["reflection"]
                            is_complete = ref.is_complete if hasattr(ref, 'is_complete') else ref.get('is_complete', False)
                            iteration = state.get("iteration", 0)
                            if is_complete:
                                console.print(f"[green]   Research complete after {iteration} iterations[/green]")
                            else:
                                gaps = ref.gaps if hasattr(ref, 'gaps') else ref.get('gaps', [])
                                console.print(f"[yellow]   Iteration {iteration}: Found {len(gaps)} knowledge gaps[/yellow]")

            # Save state periodically
            await storage.save_state(state)

        # Research completed
        state["status"] = ResearchStatus.COMPLETED
        await storage.save_state(state)

    except Exception as e:
        state["status"] = ResearchStatus.FAILED
        state["error"] = str(e)
        await storage.save_state(state)
        console.print(f"\n[red]❌ Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Display results
    console.print("\n[green]✅ Research completed![/green]\n")

    # Show findings summary
    if state.get("findings"):
        console.print(f"[bold]📚 Findings:[/bold] {len(state['findings'])} sources")
        console.print(format_findings_table(state["findings"]))
        console.print()

    # Generate and display report
    if state.get("report"):
        console.print("[bold]📝 Report:[/bold]\n")
        console.print(Markdown(state["report"]))

    # Save to file if requested
    if output_path:
        generator = ReportGenerator(state)
        generator.save(output_path, output_format)
        console.print(f"\n[green]💾 Report saved to: {output_path}[/green]")

    console.print(f"\n[dim]Job ID: {job_id}[/dim]")


@main.command()
@click.option("--id", "job_id", help="Job ID to check")
def status(job_id: Optional[str]):
    """Check research status."""
    asyncio.run(_check_status(job_id))


async def _check_status(job_id: Optional[str]):
    """Check status of research jobs."""
    config = Config.load()
    storage = Storage(config.storage.get_db_path())
    await storage.init()

    if job_id:
        state = await storage.load_state(job_id)
        if state:
            console.print(format_progress(state))
        else:
            console.print(f"[red]Job {job_id} not found[/red]")
    else:
        jobs = await storage.list_jobs(limit=10)
        if jobs:
            console.print("[bold]Recent Research Jobs:[/bold]\n")
            for job in jobs:
                status_icon = {
                    "completed": "✅",
                    "running": "🔍",
                    "paused": "⏸️",
                    "failed": "❌",
                    "pending": "⏳",
                }.get(job["status"], "❓")
                console.print(f"{status_icon} {job['id']}: {job['topic'][:50]}... [{job['status']}]")
        else:
            console.print("[dim]No research jobs found[/dim]")


@main.command()
@click.option("--id", "job_id", required=True, help="Job ID to continue")
def continue_(job_id: str):
    """Continue a paused research task."""
    console.print(f"[yellow]Continuing research {job_id}...[/yellow]")
    # Implementation similar to run, but load existing state
    asyncio.run(_continue_research(job_id))


async def _continue_research(job_id: str):
    """Continue research from saved state."""
    config = Config.load()
    storage = Storage(config.storage.get_db_path())
    await storage.init()

    state = await storage.load_state(job_id)
    if not state:
        console.print(f"[red]Job {job_id} not found[/red]")
        sys.exit(1)

    if state.get("status") == ResearchStatus.COMPLETED:
        console.print("[green]Research already completed![/green]")
        # Display report
        if state.get("report"):
            console.print(Markdown(state["report"]))
        return

    # Continue workflow from saved state
    console.print(f"[green]Resuming research: {state['topic']}[/green]")
    # TODO: Implement resume logic
    console.print("[yellow]Resume functionality coming soon...[/yellow]")


@main.command()
@click.argument("job_id")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["markdown", "json"]),
    default="markdown",
    help="Export format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    required=True,
    help="Output file path",
)
def export(job_id: str, format: str, output: Path):
    """Export research report."""
    asyncio.run(_export_report(job_id, format, output))


async def _export_report(job_id: str, format: str, output: Path):
    """Export research report to file."""
    config = Config.load()
    storage = Storage(config.storage.get_db_path())
    await storage.init()

    state = await storage.load_state(job_id)
    if not state:
        console.print(f"[red]Job {job_id} not found[/red]")
        sys.exit(1)

    generator = ReportGenerator(state)
    generator.save(output, format)
    console.print(f"[green]✅ Report exported to: {output}[/green]")


@main.group()
def config():
    """Manage configuration."""
    pass


@config.command()
@click.option("--openrouter-key", prompt="OpenRouter API Key", hide_input=True)
@click.option("--tavily-key", prompt="Tavily API Key (optional)", hide_input=True, default="")
def set(openrouter_key: str, tavily_key: str):
    """Set API keys."""
    cfg = Config.load()
    cfg.openrouter_api_key = openrouter_key
    if tavily_key:
        cfg.tavily_api_key = tavily_key
    cfg.save()
    console.print("[green]✅ Configuration saved[/green]")


@config.command()
def show():
    """Show current configuration."""
    cfg = Config.load()
    console.print("[bold]Current Configuration:[/bold]\n")
    console.print(f"OpenRouter API Key: {'✅ Set' if cfg.openrouter_api_key else '❌ Not set'}")
    console.print(f"Tavily API Key: {'✅ Set' if cfg.tavily_api_key else '❌ Not set'}")
    console.print(f"Default Search: {cfg.search.provider}")
    console.print(f"Default Model: {cfg.llm.model}")
    console.print(f"Default Depth: {cfg.defaults.depth}")


if __name__ == "__main__":
    main()
