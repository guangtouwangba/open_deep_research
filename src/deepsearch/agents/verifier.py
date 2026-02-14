"""Verification agent for cross-checking findings."""

import json
from typing import List

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from deepsearch.state import Conflict, Finding, VerifiedFinding

VERIFIER_SYSTEM_PROMPT = """You are a fact-checking expert. Cross-verify research findings and identify conflicts or confirmations.

Guidelines:
1. Compare findings from different sources
2. Identify agreements (supporting evidence)
3. Identify contradictions or conflicts
4. Assess credibility of each finding
5. Note areas needing further verification

Output format: JSON with verified_findings and conflicts."""


class VerifierAgent:
    """Agent for verifying findings."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def verify(self, findings: List[Finding]) -> List[VerifiedFinding]:
        """Cross-verify findings."""
        if not findings:
            return []

        # If few findings, simple verification
        if len(findings) <= 3:
            return [
                VerifiedFinding(
                    finding=f,
                    verification_status="unverified",
                    supporting_sources=[],
                    conflicting_sources=[],
                )
                for f in findings
            ]

        # Group findings by question for verification
        from collections import defaultdict
        by_question = defaultdict(list)
        for f in findings:
            by_question[f.question].append(f)

        verified = []
        for question, question_findings in by_question.items():
            verified.extend(await self._verify_group(question_findings))

        return verified

    async def _verify_group(self, findings: List[Finding]) -> List[VerifiedFinding]:
        """Verify a group of related findings."""
        # Simple verification based on source diversity
        sources = set(f.source for f in findings)

        verified = []
        for finding in findings:
            # Find supporting findings (similar content, different source)
            supporting = [
                f.source for f in findings
                if f.source != finding.source and self._content_similar(finding.content, f.content)
            ]

            status = "confirmed" if len(supporting) >= 2 else "unverified"
            if len(supporting) == 1:
                status = "confirmed"

            verified.append(
                VerifiedFinding(
                    finding=finding,
                    verification_status=status,
                    supporting_sources=supporting,
                    conflicting_sources=[],  # Simplified for now
                )
            )

        return verified

    def _content_similar(self, a: str, b: str) -> bool:
        """Simple content similarity check."""
        # Simple keyword overlap
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())

        if not a_words or not b_words:
            return False

        overlap = len(a_words & b_words)
        return overlap / min(len(a_words), len(b_words)) > 0.3

    async def find_conflicts(self, findings: List[Finding]) -> List[Conflict]:
        """Find conflicts between findings."""
        # Simplified conflict detection
        return []
