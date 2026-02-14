"""Report writing agent."""

from datetime import datetime
from typing import List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from deepsearch.state import ResearchDepth, Section, VerifiedFinding

# Depth-specific writing instructions
DEPTH_INSTRUCTIONS = {
    ResearchDepth.QUICK: {
        "style": "concise and focused",
        "length": "800-1200 words",
        "sections": "Executive Summary, Key Findings, Conclusions",
        "detail": "Focus on the most important points. Be direct and actionable.",
    },
    ResearchDepth.BALANCED: {
        "style": "thorough yet readable",
        "length": "1500-2500 words",
        "sections": "Executive Summary, Background, Key Findings (by theme), Analysis, Sources, Conclusions",
        "detail": "Provide context and analysis. Explain the significance of findings. Include multiple perspectives.",
    },
    ResearchDepth.COMPREHENSIVE: {
        "style": "in-depth and exhaustive",
        "length": "3000-5000 words",
        "sections": "Executive Summary, Introduction & Background, Methodology, Detailed Findings (by theme with subsections), Critical Analysis, Implications, Limitations, Sources & References, Conclusions & Recommendations",
        "detail": """Provide deep analysis with:
- Historical context and background
- Multiple viewpoints and perspectives  
- Detailed evidence and data points
- Critical evaluation of sources
- Practical implications and recommendations
- Areas for further research""",
    },
}

WRITER_SYSTEM_PROMPT = """You are an expert research report writer. Synthesize verified findings into a comprehensive, well-structured report.

Core Guidelines:
1. Organize by themes or sections
2. Use clear headings and structure (use ## for main sections, ### for subsections)
3. Cite sources appropriately with [Source: URL] format
4. Be objective and balanced
5. Highlight key insights and conclusions
6. Note any limitations or gaps
7. Use the provided "Current Date" for any date references in the report — do NOT guess or use your training cutoff date

IMPORTANT: Always write the report in the SAME LANGUAGE as the research topic. If the topic is in Chinese, write the entire report in Chinese. If in English, use English.

Format: Markdown with clear hierarchy"""


class WriterAgent:
    """Agent for writing research reports."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def write(
        self,
        verified_findings: List[VerifiedFinding],
        topic: str,
        depth: Optional[ResearchDepth] = None,
    ) -> str:
        """Write a research report with depth-appropriate detail."""
        if not verified_findings:
            return f"# Research Report: {topic}\n\nNo findings available."

        # Get depth-specific instructions
        depth = depth or ResearchDepth.BALANCED
        instructions = DEPTH_INSTRUCTIONS.get(depth, DEPTH_INSTRUCTIONS[ResearchDepth.BALANCED])

        # Build prompt
        findings_text = self._format_findings(verified_findings)

        current_date = datetime.now().strftime("%Y-%m-%d")

        user_prompt = f"""Topic: {topic}
Current Date: {current_date}

Research Depth: {depth.value.upper()}
Required Length: {instructions["length"]}
Writing Style: {instructions["style"]}

Verified Findings ({len(verified_findings)} sources):
{findings_text}

Write a {instructions["style"]} research report in Markdown format.

REQUIRED SECTIONS:
{instructions["sections"]}

DEPTH REQUIREMENTS:
{instructions["detail"]}

IMPORTANT:
- The report MUST be at least {instructions["length"].split('-')[0]} words
- Each major section should have substantive content (not just bullet points)
- Synthesize and analyze findings, don't just list them
- Draw connections between different findings
- Provide actionable insights where applicable

Report:"""

        messages = [
            SystemMessage(content=WRITER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        response = await self.llm.ainvoke(messages)
        return response.content

    def _format_findings(self, verified: List[VerifiedFinding]) -> str:
        """Format verified findings for the prompt."""
        lines = []
        for v in verified:
            f = v.finding
            lines.append(f"Question: {f.question}")
            lines.append(f"Source: {f.source}")
            lines.append(f"Title: {f.title}")
            lines.append(f"Content: {f.content}")
            lines.append(f"Verification: {v.verification_status}")
            lines.append("")
        return "\n".join(lines)

    def _create_sections(self, verified: List[VerifiedFinding]) -> List[Section]:
        """Create report sections from findings."""
        # Group by question
        from collections import defaultdict
        by_question = defaultdict(list)
        for v in verified:
            by_question[v.finding.question].append(v)

        sections = []
        for question, findings in by_question.items():
            content = "\n\n".join([
                f"- {v.finding.content} (Source: {v.finding.source})"
                for v in findings
            ])
            sections.append(
                Section(
                    title=question,
                    content=content,
                    sources=[v.finding.source for v in findings],
                )
            )

        return sections
