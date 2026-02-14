"""Research planning agent with graph structure and domain awareness."""

import json
import re
from datetime import datetime
from typing import Dict, List, Set

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from deepsearch.state import ResearchDepth, ResearchQuestion, SearchStrategy

# Domain-specific search hints
DOMAIN_HINTS = {
    SearchStrategy.ACADEMIC: {
        "keywords": ["paper", "research", "study", "arxiv", "journal", "conference", "survey"],
        "operators": ["site:arxiv.org", "site:scholar.google.com", "filetype:pdf"],
    },
    SearchStrategy.NEWS: {
        "keywords": ["news", "latest", "breaking", "report", "announced", "recently"],
        "operators": ["site:news.google.com", "site:reuters.com", "site:bloomberg.com"],
    },
    SearchStrategy.TECHNICAL: {
        "keywords": ["documentation", "docs", "github", "tutorial", "implementation", "code"],
        "operators": ["site:github.com", "site:docs.python.org", "site:readthedocs.io"],
    },
    SearchStrategy.LEGAL: {
        "keywords": ["law", "regulation", "policy", "compliance", "legal", "act"],
        "operators": ["site:gov", "site:legislation.gov.uk"],
    },
    SearchStrategy.FINANCIAL: {
        "keywords": ["stock", "market", "finance", "earnings", "revenue", "investment"],
        "operators": ["site:sec.gov", "site:finance.yahoo.com"],
    },
}

PLANNER_SYSTEM_PROMPT = """You are a research planning expert with graph structure and domain awareness.
Your task is to break down a research topic into a structured graph of questions.

Current Date: {current_date}
Topic Type: {topic_type}
Recommended Search Strategy: {search_strategy}

GRAPH STRUCTURE GUIDELINES:
1. Organize questions into categories (e.g., "background", "technical", "comparison", "future")
2. Define dependencies: some questions build on answers from others
3. Assign execution order within each category
4. Avoid duplicate or highly similar questions

QUESTION DESIGN RULES:
1. Create 3-7 questions depending on depth level
2. Each question should be specific, answerable, and non-redundant
3. Use dependencies to create a logical flow (foundation → details → synthesis)
4. Group related questions under the same category

SEARCH STRATEGY RULES:
- ACADEMIC: Use for papers, research, studies → add "site:arxiv.org", "filetype:pdf"
- NEWS: Use for current events, announcements → add time-sensitive keywords
- TECHNICAL: Use for implementation, code, docs → add "site:github.com", "documentation"
- GENERAL: Use for broad overview, concepts → standard search

TIME-AWARENESS RULES:
- Pay attention to time-sensitive keywords like "latest", "recent", "current", "new"
- When the topic implies recency, include the current year ({current_year}) in keywords
- Example: For "latest AI trends" in 2026, include ["2026", "latest AI trends"]

LANGUAGE RULES:
- The "question" and "rationale" fields: use the SAME LANGUAGE as input topic
- The "keywords" field MUST include BOTH English AND the input language
- Example: "keywords": ["大语言模型", "LLM", "large language model"]

Output format: JSON object with questions array and metadata"""


class PlannerAgent:
    """Agent for creating structured research plans with graph awareness."""

    def __init__(self, llm: BaseChatModel):
        self.llm = llm

    def _detect_domain(self, topic: str) -> SearchStrategy:
        """Detect the domain/type of research topic."""
        topic_lower = topic.lower()

        for strategy, hints in DOMAIN_HINTS.items():
            for keyword in hints["keywords"]:
                if keyword in topic_lower:
                    return strategy

        return SearchStrategy.GENERAL

    def _deduplicate_questions(self, questions: List[ResearchQuestion]) -> List[ResearchQuestion]:
        """Remove duplicate or highly similar questions."""
        if not questions:
            return questions

        unique_questions = []
        seen_signatures = set()

        for q in questions:
            # Create signature from question text (normalized)
            sig = re.sub(r'[^\w\s]', '', q.question.lower())
            sig = re.sub(r'\s+', ' ', sig).strip()

            # Skip if too similar to existing
            is_duplicate = False
            for existing_sig in seen_signatures:
                # Simple similarity: check if one contains the other
                if sig in existing_sig or existing_sig in sig:
                    is_duplicate = True
                    break
                # Check word overlap for short questions
                sig_words = set(sig.split())
                existing_words = set(existing_sig.split())
                if len(sig_words) > 0 and len(existing_words) > 0:
                    overlap = len(sig_words & existing_words) / max(len(sig_words), len(existing_words))
                    if overlap > 0.8:  # 80% word overlap
                        is_duplicate = True
                        break

            if not is_duplicate:
                seen_signatures.add(sig)
                unique_questions.append(q)

        return unique_questions

    def _build_search_operators(self, question: ResearchQuestion, strategy: SearchStrategy) -> List[str]:
        """Add domain-specific search operators based on strategy."""
        operators = list(question.search_operators)

        if strategy == SearchStrategy.ACADEMIC:
            if not any("arxiv" in op for op in operators):
                operators.append("site:arxiv.org OR site:scholar.google.com")
        elif strategy == SearchStrategy.TECHNICAL:
            if not any("github" in op for op in operators):
                operators.append("site:github.com OR site:stackoverflow.com")
        elif strategy == SearchStrategy.NEWS:
            if not any("site:" in op for op in operators):
                operators.append(f"after:{datetime.now().year - 1}")

        return operators

    async def plan(self, topic: str, depth: ResearchDepth) -> List[ResearchQuestion]:
        """Create a structured research plan with graph topology."""
        depth_questions = {
            ResearchDepth.QUICK: 3,
            ResearchDepth.BALANCED: 5,
            ResearchDepth.COMPREHENSIVE: 7,
        }

        # Detect domain for search strategy
        detected_strategy = self._detect_domain(topic)

        # Get current real-world date
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_year = now.year

        # Get domain hints
        domain_hints = DOMAIN_HINTS.get(detected_strategy, {})
        suggested_operators = domain_hints.get("operators", [])

        user_prompt = f"""Topic: {topic}
Depth: {depth.value} ({depth_questions[depth]} questions)
Current Date: {current_date}
Detected Domain: {detected_strategy.value}

Create a structured research plan with graph topology.

Respond with JSON in this format:
{{
  "categories": ["background", "technical", "comparison"],
  "questions": [
    {{
      "id": "q1",
      "question": "specific question",
      "priority": 5,
      "keywords": ["keyword1", "keyword2"],
      "rationale": "why this matters",
      "category": "background",
      "dependencies": [],
      "order": 1,
      "search_strategy": "{detected_strategy.value}",
      "search_operators": {json.dumps(suggested_operators[:2])}
    }},
    {{
      "id": "q2",
      "question": "dependent question",
      "priority": 4,
      "keywords": ["keyword3", "keyword4"],
      "rationale": "builds on q1",
      "category": "technical",
      "dependencies": ["q1"],
      "order": 2,
      "search_strategy": "{detected_strategy.value}",
      "search_operators": []
    }}
  ]
}}

GRAPH DESIGN RULES:
1. Assign each question to a category (create logical groupings)
2. Use "dependencies" to create a DAG (no circular dependencies)
3. Set "order" for execution sequence within each category
4. Root questions (background/overview) should have empty dependencies
5. Advanced questions should depend on foundational ones

TIME-AWARENESS:
- If topic implies recency, include "{current_year}" in keywords
- For news/current events, add time-sensitive operators

DOMAIN-SPECIFIC GUIDANCE ({detected_strategy.value}):
- Keywords should include: {domain_hints.get('keywords', ['general terms'])[:3]}
- Consider using operators: {suggested_operators[:2]}

LANGUAGE RULES:
- question/rationale: SAME LANGUAGE as topic
- keywords: MUST be BILINGUAL (English + topic's language)"""

        # Format system prompt
        system_prompt = PLANNER_SYSTEM_PROMPT.format(
            current_date=current_date,
            current_year=current_year,
            topic_type=detected_strategy.value,
            search_strategy=detected_strategy.value,
        )

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
            raw_questions = data.get("questions", [])

            # Convert to ResearchQuestion objects
            questions = []
            for q_data in raw_questions:
                # Ensure search_strategy is valid enum
                strategy_str = q_data.get("search_strategy", detected_strategy.value)
                try:
                    strategy = SearchStrategy(strategy_str)
                except ValueError:
                    strategy = detected_strategy

                question = ResearchQuestion(
                    id=q_data.get("id", f"q_{datetime.now().timestamp()}"),
                    question=q_data["question"],
                    priority=q_data.get("priority", 3),
                    keywords=q_data.get("keywords", []),
                    rationale=q_data.get("rationale", ""),
                    category=q_data.get("category", "general"),
                    dependencies=q_data.get("dependencies", []),
                    order=q_data.get("order", 0),
                    search_strategy=strategy,
                    search_operators=q_data.get("search_operators", []),
                )

                # Enhance with domain-specific operators
                question.search_operators = self._build_search_operators(question, strategy)
                questions.append(question)

            # Deduplicate
            questions = self._deduplicate_questions(questions)

            # Sort by dependencies and order (topological-like sort)
            questions = self._sort_questions(questions)

            return questions

        except (json.JSONDecodeError, TypeError, KeyError) as e:
            # Fallback: create a simple plan
            return [
                ResearchQuestion(
                    question=f"What is {topic}?",
                    priority=5,
                    keywords=[topic],
                    rationale="Fundamental understanding",
                    search_strategy=detected_strategy,
                )
            ]

    def _sort_questions(self, questions: List[ResearchQuestion]) -> List[ResearchQuestion]:
        """Sort questions by dependencies (topological sort)."""
        if not questions:
            return questions

        # Build id -> question map
        question_map = {q.id: q for q in questions}

        # Track visited and result
        visited = set()
        result = []

        def visit(q_id: str, path: Set[str] = None):
            if path is None:
                path = set()

            if q_id in visited:
                return
            if q_id in path:
                # Circular dependency, skip
                return

            path.add(q_id)
            q = question_map.get(q_id)
            if q:
                # Visit dependencies first
                for dep_id in q.dependencies:
                    visit(dep_id, path)
                visited.add(q_id)
                result.append(q)
            path.discard(q_id)

        # Visit all questions
        for q in questions:
            visit(q.id)

        # Sort by category and order within result
        result.sort(key=lambda x: (x.category, x.order, -x.priority))

        return result
