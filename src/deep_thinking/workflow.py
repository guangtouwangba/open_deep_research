"""LangGraph workflow for the Deep Thinking Engine with checkpoint support."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from deepsearch.agents.researcher import ResearcherAgent
from deepsearch.agents.writer import WriterAgent
from deepsearch.search.base import SearchTool
from deepsearch.state import ResearchDepth

from deep_thinking.agents.adversarial import AdversarialAgent
from deep_thinking.agents.anchor import AnchorAgent
from deep_thinking.agents.fact_checker import FactCheckAgent
from deep_thinking.domains.base import DomainPlugin, detect_domain
from deep_thinking.session import append_finding, save_session
from deep_thinking.state import (
    SessionStatus,
    ThinkingDepth,
    ThinkingPhase,
    ThinkingSession,
    ThinkingTask,
)


GENERATION_PROMPT = """You are a domain expert providing a comprehensive analysis.

TOPIC: {topic}
AUTHORITY SOURCES: {anchors}

Based on the provided authority sources, create a thorough, well-structured analysis.

RULES:
1. Ground every claim in the authority sources listed above
2. Be specific — cite chapter numbers, course modules, specific metrics
3. Include practical examples and actionable recommendations
4. Acknowledge limitations and what you're uncertain about
5. Use the SAME LANGUAGE as the topic

Provide a detailed analysis (800-1500 words)."""


SYNTHESIS_PROMPT = """Synthesize the following into a final, refined analysis.

ORIGINAL CONTENT:
{generation}

CRITIQUE POINTS:
{critiques}

VERIFICATION RESULTS:
{verifications}

{council_section}

USER CHALLENGES:
{user_challenges}

RULES:
1. Incorporate valid critique points — fix the weaknesses identified
2. Remove or flag any unverified claims
3. Strengthen the analysis based on council perspectives (if any)
4. Address user challenges directly
5. Keep the same language as the original
6. Assign a confidence score (0.0-1.0) based on verification results

Output the refined analysis followed by:
CONFIDENCE: X.XX"""


class ThinkingEngine:
    """Orchestrates the 5-phase thinking pipeline."""

    def __init__(
        self,
        llm: BaseChatModel,
        search_tool: SearchTool,
        domain: Optional[DomainPlugin] = None,
    ):
        self.llm = llm
        self.search_tool = search_tool
        self.domain = domain

        # Initialize agents
        self.anchor_agent = AnchorAgent(llm)
        self.researcher = ResearcherAgent(llm, search_tool)
        self.adversarial_agent = AdversarialAgent(llm)
        self.fact_checker = FactCheckAgent(llm, search_tool)
        self.writer = WriterAgent(llm)

    async def decompose_goal(
        self,
        session: ThinkingSession,
    ) -> ThinkingSession:
        """Phase 0: Decompose goal into anchored thinking tasks."""
        domain = self._resolve_domain(session)
        depth = ThinkingDepth(session.depth)

        tasks = await self.anchor_agent.decompose_goal(
            goal=session.goal,
            domain=domain,
            depth=depth,
        )

        session.tasks = tasks
        save_session(session)
        return session

    async def run_phase_a_b(
        self,
        session: ThinkingSession,
        task: ThinkingTask,
    ) -> ThinkingTask:
        """Phase A (Anchor) + Phase B (Generate) — runs automatically."""
        domain = self._resolve_domain(session)

        # Phase A: Enhance anchoring
        task = await self.anchor_agent.anchor_single_task(task, domain)
        task.phase = ThinkingPhase.ANCHORED

        # Phase B: Generate initial analysis using anchored topic
        anchored_topic = task.topic
        if task.anchor_output and "anchored_topic" in task.anchor_output:
            anchored_topic = task.anchor_output["anchored_topic"]

        prompt = GENERATION_PROMPT.format(
            topic=anchored_topic,
            anchors=", ".join(task.anchors) if task.anchors else "general knowledge",
        )

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        task.generation_output = response.content
        task.phase = ThinkingPhase.GENERATED

        save_session(session)
        return task

    async def run_phase_c(
        self,
        session: ThinkingSession,
        task: ThinkingTask,
    ) -> tuple[ThinkingTask, bool]:
        """
        Phase C: Adversarial Critique — CHECKPOINT 1.

        Returns: (task, should_trigger_council)
        """
        domain = self._resolve_domain(session)

        critique_points, confidence, should_council = await self.adversarial_agent.critique(
            task=task,
            generation_output=task.generation_output or "",
            domain=domain,
        )

        task.critique_points = critique_points
        task.confidence = confidence

        # Run council if triggered
        if should_council:
            task.council_triggered = True
            positions = await self.adversarial_agent.run_council(
                task=task,
                generation_output=task.generation_output or "",
                critique_points=critique_points,
                domain=domain,
            )
            task.council_positions = positions

        task.phase = ThinkingPhase.CRITIQUED
        save_session(session)
        return task, should_council

    async def run_phase_d(
        self,
        session: ThinkingSession,
        task: ThinkingTask,
    ) -> ThinkingTask:
        """Phase D: Verification — CHECKPOINT 2."""
        content = task.generation_output or ""

        # 1. Fact-check specific claims
        verified_claims, unverified_texts = await self.fact_checker.verify_task(
            task=task,
            content=content,
        )
        task.verified_claims = verified_claims
        task.unverified_claims = unverified_texts

        # 2. Search for opposition
        oppositions = await self.fact_checker.search_opposition(
            topic=task.topic,
            key_claims=[vc.claim for vc in verified_claims[:3]],
        )

        # Store opposition as additional critique
        for opp in oppositions:
            from deep_thinking.state import CritiquePoint
            task.critique_points.append(CritiquePoint(
                severity="low",
                critique=f"[反对意见] {opp}",
                suggestion="Consider incorporating this perspective",
            ))

        task.phase = ThinkingPhase.VERIFIED
        save_session(session)
        return task

    async def run_phase_e(
        self,
        session: ThinkingSession,
        task: ThinkingTask,
        user_challenges: Optional[List[str]] = None,
    ) -> ThinkingTask:
        """Phase E: Synthesize — runs automatically after user approval."""

        critiques_text = "\n".join(
            f"- [{cp.severity}] {cp.critique}" for cp in task.critique_points
        )

        verifications_text = "\n".join(
            f"- {'✅' if vc.status.value == 'confirmed' else '⚠️' if vc.status.value == 'unverified' else '❌'} {vc.claim}: {vc.notes}"
            for vc in task.verified_claims
        )

        council_section = ""
        if task.council_positions:
            council_section = "EXPERT COUNCIL POSITIONS:\n" + "\n".join(
                f"- {pos.expert_name} ({pos.perspective}): {pos.position}"
                for pos in task.council_positions
            )

        user_challenges_text = "\n".join(
            f"- {c}" for c in (user_challenges or session.user_challenges)
        ) or "None"

        prompt = SYNTHESIS_PROMPT.format(
            generation=task.generation_output or "",
            critiques=critiques_text,
            verifications=verifications_text,
            council_section=council_section,
            user_challenges=user_challenges_text,
        )

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content

        # Extract confidence from output
        if "CONFIDENCE:" in content:
            parts = content.rsplit("CONFIDENCE:", 1)
            task.synthesis = parts[0].strip()
            try:
                task.confidence = float(parts[1].strip())
            except ValueError:
                pass
        else:
            task.synthesis = content

        task.phase = ThinkingPhase.SYNTHESIZED
        task.completed_at = datetime.now()

        # Persist to findings.md
        append_finding(session, task, task.synthesis)

        # Update session
        if session.is_complete():
            session.status = SessionStatus.COMPLETED
        save_session(session)

        return task

    async def generate_final_report(self, session: ThinkingSession) -> str:
        """Generate a final comprehensive report from all findings."""
        from deepsearch.state import VerifiedFinding, Finding, ResearchDepth

        # Convert our findings to deepsearch format for the writer
        verified_findings = []
        for task in session.tasks:
            if task.synthesis:
                finding = Finding(
                    question=task.topic,
                    source="deep-thinking-engine",
                    title=task.topic,
                    content=task.synthesis,
                    credibility=task.confidence or 0.5,
                )
                vf = VerifiedFinding(
                    finding=finding,
                    verification_status="confirmed" if (task.confidence or 0) > 0.7 else "unverified",
                    supporting_sources=[vc.source_url for vc in task.verified_claims if vc.source_url],
                )
                verified_findings.append(vf)

        depth_map = {
            ThinkingDepth.QUICK: ResearchDepth.QUICK,
            ThinkingDepth.BALANCED: ResearchDepth.BALANCED,
            ThinkingDepth.COMPREHENSIVE: ResearchDepth.COMPREHENSIVE,
        }

        report = await self.writer.write(
            verified_findings=verified_findings,
            topic=session.goal,
            depth=depth_map.get(ThinkingDepth(session.depth), ResearchDepth.BALANCED),
        )

        return report

    def _resolve_domain(self, session: ThinkingSession) -> Optional[DomainPlugin]:
        """Resolve the domain for a session."""
        if self.domain:
            return self.domain
        if session.domain and session.domain != "auto":
            from deep_thinking.domains.base import get_domain
            return get_domain(session.domain)
        return detect_domain(session.goal)
