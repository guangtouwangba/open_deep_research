"""Reflection agent for evaluating research progress."""

import json
from typing import List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from deepsearch.state import Finding, ReflectionResult, ResearchQuestion

REFLECTOR_SYSTEM_PROMPT = """You are a research quality evaluator. Assess research findings and determine if more research is needed.

Guidelines:
1. Evaluate coverage of the original questions
2. Identify knowledge gaps or missing information
3. Check for conflicting information that needs resolution
4. Suggest new angles or questions if needed
5. Decide if research is complete or should continue

IMPORTANT: Always respond in the SAME LANGUAGE as the original research topic and questions. If they are in Chinese, use Chinese. If in English, use English.

Output format: JSON with is_complete, gaps, new_questions, and reasoning."""


class ReflectorAgent:
    """Agent for reflecting on research progress."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def reflect(
        self,
        findings: List[Finding],
        plan: List[ResearchQuestion],
        iteration: int,
        max_iterations: int,
    ) -> ReflectionResult:
        """Reflect on research progress and decide next steps."""
        # Check iteration limit
        if iteration >= max_iterations:
            return ReflectionResult(
                is_complete=True,
                gaps=[],
                new_questions=[],
                reasoning="Maximum iterations reached",
            )

        # Build reflection prompt
        questions_status = []
        for q in plan:
            related_findings = [f for f in findings if f.question == q.question]
            questions_status.append({
                "question": q.question,
                "findings_count": len(related_findings),
                "priority": q.priority,
            })

        user_prompt = f"""Iteration: {iteration}/{max_iterations}

Original Questions:
{json.dumps(questions_status, indent=2)}

Findings Summary:
{self._summarize_findings(findings)}

Assess the research and respond with JSON:
{{
  "is_complete": true/false,
  "gaps": ["gap1", "gap2"],
  "new_questions": [
    {{"question": "...", "priority": 3, "keywords": ["..."], "rationale": "..."}}
  ],
  "reasoning": "explanation"
}}"""

        messages = [
            SystemMessage(content=REFLECTOR_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content

            # Extract JSON
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                content = content[start : end + 1]

            data = json.loads(content)
            return ReflectionResult(**data)
        except (json.JSONDecodeError, TypeError):
            # Fallback: assume complete if we have findings
            return ReflectionResult(
                is_complete=len(findings) > 0 or iteration >= max_iterations - 1,
                gaps=[],
                new_questions=[],
                reasoning="Fallback completion check",
            )

    def _summarize_findings(self, findings: List[Finding]) -> str:
        """Create a brief summary of findings."""
        if not findings:
            return "No findings yet"

        summary = f"Total findings: {len(findings)}\n"
        sources = set(f.source for f in findings)
        summary += f"Unique sources: {len(sources)}\n"

        # Group by question
        from collections import defaultdict
        by_question = defaultdict(list)
        for f in findings:
            by_question[f.question].append(f)

        summary += "\nBy question:\n"
        for q, fs in by_question.items():
            summary += f"- {q}: {len(fs)} findings\n"

        return summary
