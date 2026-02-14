"""Research execution agent with domain-aware search strategies."""

from typing import List, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from deepsearch.search.base import SearchTool
from deepsearch.state import (
    Finding,
    ResearchDepth,
    ResearchQuestion,
    SearchRecord,
    SearchStrategy,
)

RESEARCHER_SYSTEM_PROMPT = """You are a research analyst. Synthesize search results into clear, factual findings.

Guidelines:
1. Extract key facts and insights from search results
2. Cite sources clearly
3. Be objective and balanced
4. Note any uncertainties or contradictions
5. Focus on answering the specific question"""

# Depth-based configuration
DEPTH_CONFIG = {
    ResearchDepth.QUICK: {
        "max_results_per_query": 3,
        "max_queries": 1,
        "max_findings": 3,
    },
    ResearchDepth.BALANCED: {
        "max_results_per_query": 5,
        "max_queries": 2,
        "max_findings": 5,
    },
    ResearchDepth.COMPREHENSIVE: {
        "max_results_per_query": 8,
        "max_queries": 3,
        "max_findings": 8,
    },
}


class ResearcherAgent:
    """Agent for executing research on a question."""

    def __init__(self, llm: BaseChatModel, search_tool: SearchTool):
        self.llm = llm
        self.search_tool = search_tool
        self.depth = ResearchDepth.BALANCED  # Default depth

    def set_depth(self, depth: ResearchDepth):
        """Set the research depth level."""
        self.depth = depth

    async def research(self, question: ResearchQuestion) -> List[Finding]:
        """Research a single question."""
        config = DEPTH_CONFIG.get(self.depth, DEPTH_CONFIG[ResearchDepth.BALANCED])
        
        # Build search queries from question and keywords
        queries = self._build_queries(question, config["max_queries"])

        all_results = []
        for query in queries:
            results = await self.search_tool.search(query, max_results=config["max_results_per_query"])
            all_results.extend(results)

        # Record search
        search_record = SearchRecord(
            query=question.question,
            provider=self.search_tool.get_name(),
            results_count=len(all_results),
        )

        # Synthesize findings
        findings = await self._synthesize_findings(question, all_results, config["max_findings"])

        return findings, search_record

    def _build_queries(self, question: ResearchQuestion, max_queries: int) -> List[str]:
        """Build domain-aware search queries from question."""
        queries = []

        # Build base query from question
        base_query = question.question

        # Add search operators if specified
        operators = " ".join(question.search_operators) if question.search_operators else ""

        # Strategy-specific query enhancement
        if question.search_strategy == SearchStrategy.ACADEMIC:
            # Academic: focus on papers, add scholarly operators
            queries.append(f"{base_query} {operators}".strip())
            if question.keywords:
                queries.append(f"{' '.join(question.keywords[:3])} paper research {operators}".strip())

        elif question.search_strategy == SearchStrategy.NEWS:
            # News: time-sensitive, recent
            queries.append(f"{base_query} {operators}".strip())
            if question.keywords:
                queries.append(f"{' '.join(question.keywords[:3])} latest news {operators}".strip())

        elif question.search_strategy == SearchStrategy.TECHNICAL:
            # Technical: documentation, implementation
            queries.append(f"{base_query} {operators}".strip())
            if question.keywords:
                queries.append(f"{' '.join(question.keywords[:3])} documentation tutorial {operators}".strip())

        else:
            # General strategy
            queries.append(base_query)
            if question.keywords:
                keyword_query = " ".join(question.keywords[:3])
                if keyword_query != base_query:
                    queries.append(f"{keyword_query} {operators}".strip())

        # Deduplicate while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            normalized = q.lower().strip()
            if normalized not in seen and normalized:
                seen.add(normalized)
                unique_queries.append(q)

        return unique_queries[:max_queries]

    async def _synthesize_findings(
        self, question: ResearchQuestion, results: List, max_findings: int
    ) -> List[Finding]:
        """Synthesize search results into findings."""
        if not results:
            return []

        # Remove duplicates by URL
        seen_urls = set()
        unique_results = []
        for r in results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        # Create findings from top results based on depth
        findings = []
        for i, result in enumerate(unique_results[:max_findings]):
            # Credibility scoring based on position and source
            credibility = max(0.5, 0.9 - (i * 0.05))
            
            finding = Finding(
                question=question.question,
                source=result.url,
                title=result.title,
                content=result.snippet,
                credibility=credibility,
            )
            findings.append(finding)

        return findings
