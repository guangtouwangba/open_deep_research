"""CLI for the Deep Thinking Engine."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from deep_thinking.config import ThinkingConfig, ensure_state_dir
from deep_thinking.domains.base import detect_domain, get_domain, list_domains
from deep_thinking.session import create_session, list_sessions, load_session, save_session
from deep_thinking.state import ThinkingDepth, ThinkingPhase

console = Console()


def _create_engine(domain_name: Optional[str] = None):
    """Create ThinkingEngine with configured LLM and search tool."""
    from dotenv import load_dotenv
    load_dotenv()

    from deepsearch.config import Config
    from deepsearch.search.tavily import TavilySearchTool
    from deepsearch.search.openrouter import OpenRouterSearchTool
    from deep_thinking.workflow import ThinkingEngine

    config = Config.load()

    # Create LLM
    from deepsearch.workflow import create_llm
    llm = create_llm({
        "provider": config.llm.provider,
        "model": config.llm.model,
        "api_key": config.get_llm_api_key(),
    })

    # Create search tool
    search_api_key = config.get_search_api_key()
    if config.search.provider == "tavily" and config.tavily_api_key:
        search_tool = TavilySearchTool(api_key=config.tavily_api_key)
    else:
        search_tool = OpenRouterSearchTool(
            api_key=config.openrouter_api_key or "",
            model=config.search.model,
        )

    # Resolve domain
    domain = None
    if domain_name and domain_name != "auto":
        domain = get_domain(domain_name)

    return ThinkingEngine(llm=llm, search_tool=search_tool, domain=domain)


async def _run_session(
    session_id: str,
    auto: bool = False,
):
    """Run the thinking pipeline for a session."""
    session = load_session(session_id)
    if not session:
        console.print(f"[red]Session not found: {session_id}[/red]")
        return

    engine = _create_engine(session.domain)

    # Decompose goal if no tasks yet
    if not session.tasks:
        with console.status("[bold blue]Decomposing goal into thinking tasks..."):
            session = await engine.decompose_goal(session)

        console.print(f"\n[bold green]🎯 Goal decomposed into {len(session.tasks)} tasks[/bold green]")
        for i, task in enumerate(session.tasks):
            anchors = ", ".join(task.anchors[:2]) if task.anchors else "—"
            console.print(f"  {i+1}. {task.topic} [dim]({anchors})[/dim]")
        console.print()

    # Process tasks one by one
    while True:
        task = session.current_task()
        if task is None:
            break

        completed, total = session.progress()
        console.rule(f"[bold]Task {completed + 1}/{total}: {task.topic}")

        # Phase A + B (automatic)
        if task.phase in (ThinkingPhase.PENDING, ThinkingPhase.ANCHORED):
            with console.status("[blue]Phase A: Anchoring..."):
                pass  # Included in run_phase_a_b
            with console.status("[blue]Phase A+B: Anchoring & Generating..."):
                task = await engine.run_phase_a_b(session, task)
            console.print("[green]  ✅ Phase A (Anchor) + Phase B (Generate) complete[/green]")

        # Phase C — CHECKPOINT 1
        if task.phase == ThinkingPhase.GENERATED:
            with console.status("[yellow]Phase C: Adversarial Critique..."):
                task, council_triggered = await engine.run_phase_c(session, task)

            _display_critique(task, council_triggered)

            if not auto:
                user_input = Prompt.ask(
                    "\n[bold]Add your own challenges[/bold] (Enter to skip)",
                    default="",
                )
                if user_input.strip():
                    session.user_challenges.append(user_input.strip())

        # Phase D — CHECKPOINT 2
        if task.phase == ThinkingPhase.CRITIQUED:
            with console.status("[yellow]Phase D: Verifying claims..."):
                task = await engine.run_phase_d(session, task)

            _display_verification(task)

            if not auto:
                proceed = Confirm.ask(
                    "\n[bold]Accept and continue?[/bold]",
                    default=True,
                )
                if not proceed:
                    edit_input = Prompt.ask(
                        "What should be changed?",
                        default="",
                    )
                    if edit_input.strip():
                        session.user_challenges.append(edit_input.strip())

        # Phase E (automatic)
        if task.phase == ThinkingPhase.VERIFIED:
            with console.status("[blue]Phase E: Synthesizing..."):
                task = await engine.run_phase_e(session, task)

            confidence_color = "green" if (task.confidence or 0) > 0.7 else "yellow"
            console.print(
                f"[{confidence_color}]  ✅ Phase E complete "
                f"(confidence: {task.confidence:.2f})[/{confidence_color}]"
            )

    # All tasks complete
    console.print()
    console.rule("[bold green]All tasks complete!")

    completed, total = session.progress()
    console.print(f"[green]Completed {completed}/{total} tasks[/green]")

    # Generate final report
    if Confirm.ask("\n[bold]Generate final report?[/bold]", default=True):
        with console.status("[blue]Generating comprehensive report..."):
            report = await engine.generate_final_report(session)

        report_path = Path.home() / ".thinking-agent" / "sessions" / session.session_id / "report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        console.print(f"\n[green]Report saved to: {report_path}[/green]")
        console.print(Panel(report[:2000] + "\n...", title="Report Preview"))


def _display_critique(task, council_triggered: bool):
    """Display Phase C critique results."""
    console.print("\n[bold yellow]★ CHECKPOINT: Adversarial Critique[/bold yellow]")

    for cp in task.critique_points:
        severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(cp.severity, "⚪")
        console.print(f"  {severity_icon} [{cp.severity}] {cp.critique}")
        if cp.suggestion:
            console.print(f"     → {cp.suggestion}")

    council_status = "⚡ Council TRIGGERED" if council_triggered else "⚡ Council not triggered"
    confidence_str = f"confidence: {task.confidence:.2f}" if task.confidence else ""
    console.print(f"  {council_status} ({confidence_str})")

    if task.council_positions:
        console.print("\n  [bold]Expert Council Debate:[/bold]")
        for pos in task.council_positions:
            console.print(f"    [cyan]{pos.expert_name}[/cyan] ({pos.perspective}):")
            console.print(f"      {pos.position[:200]}...")


def _display_verification(task):
    """Display Phase D verification results."""
    console.print("\n[bold yellow]★ CHECKPOINT: Verification Results[/bold yellow]")

    for vc in task.verified_claims:
        icon = {
            "confirmed": "✅",
            "disputed": "❌",
            "unverified": "⚠️",
        }.get(vc.status.value, "❓")
        console.print(f"  {icon} {vc.claim}")
        if vc.notes:
            console.print(f"     {vc.notes}")

    if task.unverified_claims:
        console.print(f"\n  [yellow]⚠️ {len(task.unverified_claims)} claims could not be verified[/yellow]")


@click.group(invoke_without_command=True)
@click.argument("goal", required=False)
@click.option("--domain", "-d", default="auto", help="Domain: learning, research, investment, tech-eval, content-creation, game-dev")
@click.option("--depth", default="balanced", type=click.Choice(["quick", "balanced", "comprehensive"]))
@click.option("--resume", "-r", default=None, help="Resume a session by ID")
@click.option("--auto", is_flag=True, help="Skip checkpoints, run fully autonomous")
@click.option("--list", "list_all", is_flag=True, help="List all sessions")
@click.option("--status", "status_id", default=None, help="Show session status")
@click.pass_context
def main(ctx, goal, domain, depth, resume, auto, list_all, status_id):
    """Deep Thinking Engine — structured, verified knowledge through iterative reasoning."""
    ensure_state_dir()

    if list_all:
        _cmd_list()
        return

    if status_id:
        _cmd_status(status_id)
        return

    if resume:
        asyncio.run(_run_session(resume, auto=auto))
        return

    if goal:
        # Create new session
        session = create_session(goal=goal, domain=domain, depth=depth)

        # Auto-detect domain if needed
        if domain == "auto":
            detected = detect_domain(goal)
            if detected:
                session.domain = detected.name
                save_session(session)
                console.print(f"[dim]Auto-detected domain: {detected.display_name}[/dim]")

        console.print(f"[green]📂 Session: {session.session_id}[/green]")
        asyncio.run(_run_session(session.session_id, auto=auto))
    else:
        # No arguments — show help or list sessions
        click.echo(ctx.get_help())


def _cmd_list():
    """List all sessions."""
    sessions = list_sessions()
    if not sessions:
        console.print("[dim]No sessions found.[/dim]")
        return

    table = Table(title="Thinking Sessions")
    table.add_column("Session ID", style="cyan")
    table.add_column("Goal", max_width=40)
    table.add_column("Domain")
    table.add_column("Progress")
    table.add_column("Status")
    table.add_column("Updated")

    for s in sessions:
        progress = f"{s['tasks_completed']}/{s['tasks_total']}"
        status_color = {"active": "yellow", "completed": "green", "paused": "dim"}.get(s["status"], "white")
        table.add_row(
            s["session_id"],
            s["goal"][:40],
            s.get("domain", "—"),
            progress,
            f"[{status_color}]{s['status']}[/{status_color}]",
            str(s.get("updated_at", ""))[:16],
        )

    console.print(table)


def _cmd_status(session_id: str):
    """Show detailed session status."""
    session = load_session(session_id)
    if not session:
        console.print(f"[red]Session not found: {session_id}[/red]")
        return

    console.print(Panel(
        f"[bold]{session.goal}[/bold]\n"
        f"Domain: {session.domain} | Depth: {session.depth} | Status: {session.status.value}",
        title=f"Session: {session.session_id}",
    ))

    for i, task in enumerate(session.tasks):
        phase_icons = {
            "pending": "⬜",
            "anchored": "🔵",
            "generated": "🟡",
            "critiqued": "🟠",
            "verified": "🟣",
            "synthesized": "🟢",
        }
        icon = phase_icons.get(task.phase.value, "❓")
        confidence_str = f" [{task.confidence:.2f}]" if task.confidence else ""
        console.print(f"  {icon} {task.id}: {task.topic} — {task.phase.value}{confidence_str}")


if __name__ == "__main__":
    main()
