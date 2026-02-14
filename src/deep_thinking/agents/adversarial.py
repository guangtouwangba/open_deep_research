"""AdversarialAgent — red-team critique and expert council simulation."""

import json
from typing import List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from deep_thinking.domains.base import DomainPlugin, Expert
from deep_thinking.state import CouncilPosition, CritiquePoint, ThinkingTask


ADVERSARIAL_SYSTEM_PROMPT = """You are the harshest, most rigorous critic in the domain of {domain}.
Your job is to DESTROY weak thinking. You are NOT helpful — you are adversarial.

CRITIQUE GUIDELINES:
1. Attack theoretical content that lacks practical application
2. Identify outdated information or sources
3. Flag "learning for learning's sake" — content with no real-world value
4. Point out missing critical details that practitioners would know
5. Challenge assumptions and biases
6. Identify where the analysis is shallow or hand-wavy
7. Check for survivorship bias, confirmation bias, and authority bias

SEVERITY LEVELS:
- high: Fundamentally flawed, would lead to wrong conclusions
- medium: Significant weakness, needs correction
- low: Minor issue, could be improved

IMPORTANT: Respond in the SAME LANGUAGE as the content being critiqued.

Output JSON:
{{
  "critique_points": [
    {{
      "severity": "high|medium|low",
      "critique": "specific criticism",
      "suggestion": "how to fix it"
    }}
  ],
  "overall_confidence": 0.0-1.0,
  "has_fundamental_disagreements": true/false,
  "recommended_council": true/false
}}"""


COUNCIL_SYSTEM_PROMPT = """You are moderating a panel debate between domain experts.

EXPERTS:
{experts_desc}

TOPIC: {topic}

RULES:
1. Each expert speaks from their unique perspective and authority source
2. Experts MUST disagree with each other on at least some points
3. Each expert must rebut at least one other expert's position
4. The debate should reveal genuine trade-offs, not false consensus
5. After all experts speak, synthesize a balanced path forward

IMPORTANT: Respond in the SAME LANGUAGE as the topic.

Output JSON:
{{
  "positions": [
    {{
      "expert_name": "name",
      "perspective": "school of thought",
      "position": "their full argument",
      "rebuttals": ["rebuttal to expert X", "rebuttal to expert Y"]
    }}
  ],
  "synthesis": "balanced conclusion incorporating all perspectives",
  "key_tradeoffs": ["tradeoff 1", "tradeoff 2"]
}}"""


class AdversarialAgent:
    """Agent for adversarial critique and expert council simulation."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    async def critique(
        self,
        task: ThinkingTask,
        generation_output: str,
        domain: Optional[DomainPlugin] = None,
    ) -> tuple[List[CritiquePoint], float, bool]:
        """
        Perform adversarial critique on generated content.

        Returns: (critique_points, confidence, should_trigger_council)
        """
        domain_name = domain.display_name if domain else "this field"

        system_prompt = ADVERSARIAL_SYSTEM_PROMPT.format(domain=domain_name)

        user_prompt = f"""TOPIC: {task.topic}

AUTHORITY SOURCES CLAIMED: {', '.join(task.anchors)}

CONTENT TO CRITIQUE:
{generation_output}

Tear this apart. Find every weakness, every gap, every questionable claim.
Be specific — don't just say "needs more detail", say WHAT detail is missing and WHY it matters."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content

            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                content = content[start : end + 1]

            data = json.loads(content)

            critique_points = [
                CritiquePoint(**cp) for cp in data.get("critique_points", [])
            ]
            confidence = data.get("overall_confidence", 0.5)
            should_council = data.get("recommended_council", False)

            # Also check domain-level council triggers
            if domain and domain.should_trigger_council(task.topic):
                should_council = True

            return critique_points, confidence, should_council

        except (json.JSONDecodeError, TypeError):
            return [
                CritiquePoint(
                    severity="low",
                    critique="Unable to perform structured critique",
                    suggestion="Manual review recommended",
                )
            ], 0.5, False

    async def run_council(
        self,
        task: ThinkingTask,
        generation_output: str,
        critique_points: List[CritiquePoint],
        experts: Optional[List[Expert]] = None,
        domain: Optional[DomainPlugin] = None,
    ) -> List[CouncilPosition]:
        """
        Run an expert council debate on the topic.

        Uses domain-configured experts or falls back to generic experts.
        """
        if experts is None and domain:
            experts = domain.council_experts
        if not experts:
            experts = [
                Expert(
                    name="Theorist",
                    perspective="Academic rigor",
                    anchor_source="peer-reviewed research",
                    style="cautious",
                ),
                Expert(
                    name="Practitioner",
                    perspective="Real-world application",
                    anchor_source="industry experience",
                    style="pragmatic",
                ),
                Expert(
                    name="Contrarian",
                    perspective="Devil's advocate",
                    anchor_source="alternative approaches",
                    style="aggressive",
                ),
            ]

        experts_desc = "\n".join(
            f"- {e.name} ({e.perspective}): Draws from {e.anchor_source}. Style: {e.style}"
            for e in experts
        )

        critique_summary = "\n".join(
            f"- [{cp.severity}] {cp.critique}" for cp in critique_points
        )

        system_prompt = COUNCIL_SYSTEM_PROMPT.format(
            experts_desc=experts_desc,
            topic=task.topic,
        )

        user_prompt = f"""CONTENT UNDER DEBATE:
{generation_output}

CRITIQUE POINTS RAISED:
{critique_summary}

Now let each expert weigh in. They should address both the content and the critiques.
Each expert must offer their unique perspective and rebut at least one other expert."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            content = response.content

            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1:
                content = content[start : end + 1]

            data = json.loads(content)

            positions = [
                CouncilPosition(**p) for p in data.get("positions", [])
            ]
            return positions

        except (json.JSONDecodeError, TypeError):
            return []
