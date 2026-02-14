"""Output formatters for DeepSearch."""

from typing import List

from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from deepsearch.state import Finding, VerifiedFinding


def format_findings_table(findings: List[Finding]) -> Table:
    """Format findings as a Rich table."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Question", style="cyan", no_wrap=True)
    table.add_column("Source", style="blue")
    table.add_column("Title", style="green")
    table.add_column("Credibility", style="yellow")

    for f in findings:
        credibility = "⭐" * int(f.credibility * 5)
        table.add_row(
            f.question[:50] + "..." if len(f.question) > 50 else f.question,
            f.source[:40] + "..." if len(f.source) > 40 else f.source,
            f.title[:50] + "..." if len(f.title) > 50 else f.title,
            credibility,
        )

    return table


def format_verified_findings(verified: List[VerifiedFinding]) -> Table:
    """Format verified findings as a Rich table."""
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Question", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Source", style="blue")

    status_colors = {
        "confirmed": "[green]✓ Confirmed[/green]",
        "disputed": "[red]✗ Disputed[/red]",
        "unverified": "[yellow]? Unverified[/yellow]",
    }

    for v in verified:
        status = status_colors.get(v.verification_status, v.verification_status)
        table.add_row(
            v.finding.question[:50] + "..." if len(v.finding.question) > 50 else v.finding.question,
            status,
            v.finding.source[:40] + "..." if len(v.finding.source) > 40 else v.finding.source,
        )

    return table


def format_report_markdown(report: str) -> Markdown:
    """Format report as Rich Markdown."""
    return Markdown(report)


def format_progress(state: dict) -> str:
    """Format research progress as string."""
    lines = []

    # Status indicator
    status = state.get("status", "unknown")
    status_icons = {
        "pending": "⏳",
        "running": "🔍",
        "paused": "⏸️",
        "completed": "✅",
        "failed": "❌",
    }
    lines.append(f"{status_icons.get(status, '❓')} Status: {status.upper()}")

    # Progress
    plan = state.get("plan", [])
    idx = state.get("current_question_index", 0)
    iteration = state.get("iteration", 0)
    max_iter = state.get("max_iterations", 5)

    if plan:
        lines.append(f"📋 Questions: {idx}/{len(plan)} completed")
        lines.append(f"🔄 Iteration: {iteration}/{max_iter}")

    # Findings
    findings = state.get("findings", [])
    if findings:
        lines.append(f"📚 Findings: {len(findings)} sources collected")

    # Current activity
    if status == "running":
        if idx < len(plan):
            current_q = plan[idx].question if idx < len(plan) else "Finalizing"
            lines.append(f"🔎 Current: {current_q[:60]}...")

    return "\n".join(lines)
