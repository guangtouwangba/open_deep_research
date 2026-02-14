"""Report generation for DeepSearch."""

import json
from pathlib import Path
from typing import Optional

from deepsearch.state import ResearchState


class ReportGenerator:
    """Generate research reports in various formats."""

    def __init__(self, state: ResearchState):
        self.state = state

    def to_markdown(self) -> str:
        """Generate Markdown report."""
        if self.state.get("report"):
            return self.state["report"]

        # Fallback: generate simple report
        lines = [
            f"# Research Report: {self.state['topic']}",
            "",
            "## Summary",
            "",
            f"- **Topic**: {self.state['topic']}",
            f"- **Depth**: {self.state.get('depth', 'balanced')}",
            f"- **Findings**: {len(self.state.get('findings', []))} sources",
            "",
            "## Key Findings",
            "",
        ]

        for finding in self.state.get("findings", []):
            lines.extend([
                f"### {finding.title}",
                "",
                f"{finding.content}",
                "",
                f"*Source: [{finding.source}]({finding.source})*",
                "",
            ])

        return "\n".join(lines)

    def to_json(self) -> str:
        """Generate JSON report."""
        data = {
            "topic": self.state["topic"],
            "depth": self.state.get("depth"),
            "status": self.state.get("status"),
            "findings_count": len(self.state.get("findings", [])),
            "report": self.state.get("report", ""),
            "findings": [
                {
                    "question": f.question,
                    "title": f.title,
                    "source": f.source,
                    "content": f.content,
                    "credibility": f.credibility,
                }
                for f in self.state.get("findings", [])
            ],
        }
        return json.dumps(data, indent=2, default=str)

    def save(self, path: Path, format: Optional[str] = None) -> None:
        """Save report to file."""
        format = format or path.suffix.lstrip(".")

        if format == "md" or format == "markdown":
            content = self.to_markdown()
        elif format == "json":
            content = self.to_json()
        else:
            content = self.to_markdown()

        path.write_text(content, encoding="utf-8")
