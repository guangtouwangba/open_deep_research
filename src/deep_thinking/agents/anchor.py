"""AnchorAgent — wraps PlannerAgent with authority-source anchoring."""

import json
from datetime import datetime
from typing import List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from deepsearch.agents.planner import PlannerAgent
from deepsearch.state import ResearchDepth, ResearchQuestion

from deep_thinking.domains.base import DomainPlugin, detect_domain
from deep_thinking.state import ThinkingDepth, ThinkingTask


ANCHOR_SYSTEM_PROMPT = """You are a research planning expert that creates ANCHORED questions.

CRITICAL RULES:
1. NEVER ask open-ended questions like "What is X?" or "Tell me about X"
2. EVERY question MUST reference at least one authoritative source
3. Questions should constrain the AI's search space to high-quality knowledge

ANCHORING PATTERN:
❌ BAD: "What are the best practices for system design?"
✅ GOOD: "According to Google's SRE book and Martin Kleppmann's 'Designing Data-Intensive Applications', what are the key principles for designing fault-tolerant distributed systems?"

❌ BAD: "How do I learn machine learning?"
✅ GOOD: "Based on Andrew Ng's CS229 curriculum and fast.ai's practical approach, what is the optimal learning sequence for ML fundamentals, including specific textbook chapters and lab projects?"

DOMAIN CONTEXT:
{domain_context}

AUTHORITY SOURCES FOR THIS TOPIC:
{authority_sources}

ANCHOR TEMPLATES:
{anchor_templates}

Create {num_tasks} anchored thinking tasks for the given goal.
Each task must:
1. Reference specific authoritative sources
2. Ask for concrete, verifiable information (book chapters, course modules, specific metrics)
3. Be ordered from foundational → advanced

Current Date: {current_date}

Output JSON:
{{
  "tasks": [
    {{
      "id": "t1",
      "topic": "anchored question/topic",
      "anchors": ["MIT 18.S096", "Shreve Chapter 3"],
      "priority": 5,
      "category": "foundation"
    }}
  ]
}}"""


class AnchorAgent:
    """Creates anchored thinking tasks by wrapping PlannerAgent with domain knowledge."""

    def __init__(self, llm: BaseChatModel, planner: Optional[PlannerAgent] = None):
        self.llm = llm
        self.planner = planner or PlannerAgent(llm)

    async def decompose_goal(
        self,
        goal: str,
        domain: Optional[DomainPlugin] = None,
        depth: ThinkingDepth = ThinkingDepth.BALANCED,
    ) -> List[ThinkingTask]:
        """Decompose a goal into anchored thinking tasks."""

        # Auto-detect domain if not provided
        if domain is None:
            domain = detect_domain(goal)

        # Determine task count based on depth
        task_counts = {
            ThinkingDepth.QUICK: 4,
            ThinkingDepth.BALANCED: 7,
            ThinkingDepth.COMPREHENSIVE: 12,
        }
        num_tasks = task_counts.get(depth, 7)

        # Get domain-specific anchoring context
        if domain:
            authority_sources = domain.get_anchors_for_topic(goal)
            domain_context = f"Domain: {domain.display_name}"
            anchor_templates = "\n".join(f"- {t}" for t in domain.anchor_templates)
            authority_str = "\n".join(f"- {s}" for s in authority_sources)
        else:
            domain_context = "Domain: General (no specific domain detected)"
            anchor_templates = '- "Based on {sources}, analyze {topic}..."'
            authority_str = "- Use the most authoritative sources you know for this topic"

        # Build prompt
        system_prompt = ANCHOR_SYSTEM_PROMPT.format(
            domain_context=domain_context,
            authority_sources=authority_str,
            anchor_templates=anchor_templates,
            num_tasks=num_tasks,
            current_date=datetime.now().strftime("%Y-%m-%d"),
        )

        user_prompt = f"""Goal: {goal}
Depth: {depth.value} ({num_tasks} tasks)

Create {num_tasks} anchored thinking tasks. Remember:
- Each task MUST reference specific authoritative sources
- Order from foundational → advanced
- Use the SAME LANGUAGE as the goal"""

        messages = [
            SystemMessage(content=system_prompt),
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
            raw_tasks = data.get("tasks", [])

            tasks = []
            for i, t in enumerate(raw_tasks):
                task = ThinkingTask(
                    id=t.get("id", f"t{i + 1}"),
                    topic=t["topic"],
                    anchors=t.get("anchors", []),
                )
                tasks.append(task)

            return tasks

        except (json.JSONDecodeError, TypeError, KeyError):
            # Fallback: create a single task from the goal
            return [
                ThinkingTask(
                    id="t1",
                    topic=goal,
                    anchors=[],
                )
            ]

    async def anchor_single_task(
        self,
        task: ThinkingTask,
        domain: Optional[DomainPlugin] = None,
    ) -> ThinkingTask:
        """Enhance a single task with better anchoring."""
        if domain and not task.anchors:
            anchors = domain.get_anchors_for_topic(task.topic)
            task.anchors = anchors[:3]

        if domain and task.anchors:
            # Rewrite the topic to be properly anchored
            anchored_topic = domain.format_anchor_prompt(task.topic, task.anchors)
            task.anchor_output = {
                "original_topic": task.topic,
                "anchored_topic": anchored_topic,
                "sources": task.anchors,
            }

        return task
