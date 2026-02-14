"""FactCheckAgent — real web-based verification of claims."""

import json
import re
from typing import List, Optional, Tuple

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from deepsearch.search.base import SearchTool

from deep_thinking.state import ThinkingTask, VerificationStatus, VerifiedClaim


CLAIM_EXTRACTOR_PROMPT = """Extract all verifiable factual claims from the following content.

A verifiable claim is something that can be checked against external sources:
- Book titles and authors (can be checked on Amazon/Google Books)
- Course names and universities (can be checked on university websites)
- Tool/library names (can be checked on GitHub/npm/PyPI)
- Statistics or metrics (can be checked against original reports)
- Historical facts or events (can be checked in references)
- Company names or product names (can be checked online)

Do NOT extract:
- Opinions or subjective assessments
- General knowledge that doesn't need verification
- Vague statements without specific claims

Content:
{content}

Output JSON:
{{
  "claims": [
    {{
      "claim": "specific factual claim to verify",
      "type": "book|course|tool|statistic|fact|entity",
      "search_query": "what to search for to verify this"
    }}
  ]
}}"""


VERIFY_PROMPT = """Based on the search results below, determine if this claim is true.

CLAIM: {claim}
TYPE: {claim_type}

SEARCH RESULTS:
{search_results}

Respond with JSON:
{{
  "status": "confirmed|disputed|unverified",
  "source_url": "best supporting URL or null",
  "notes": "brief explanation of verification result"
}}"""


class FactCheckAgent:
    """Agent that performs real web-based fact-checking."""

    def __init__(self, llm: BaseChatModel, search_tool: SearchTool):
        self.llm = llm
        self.search_tool = search_tool

    async def verify_task(
        self,
        task: ThinkingTask,
        content: str,
        max_claims: int = 10,
    ) -> Tuple[List[VerifiedClaim], List[str]]:
        """
        Verify all claims in a task's generated content.

        Returns: (verified_claims, unverified_claim_texts)
        """
        # Step 1: Extract verifiable claims
        claims = await self._extract_claims(content)
        claims = claims[:max_claims]

        if not claims:
            return [], []

        # Step 2: Verify each claim via web search
        verified = []
        unverified_texts = []

        for claim_data in claims:
            claim_text = claim_data["claim"]
            claim_type = claim_data.get("type", "fact")
            search_query = claim_data.get("search_query", claim_text)

            vc = await self._verify_single_claim(claim_text, claim_type, search_query)
            verified.append(vc)

            if vc.status == VerificationStatus.UNVERIFIED:
                unverified_texts.append(claim_text)

        return verified, unverified_texts

    async def search_opposition(
        self,
        topic: str,
        key_claims: List[str],
    ) -> List[str]:
        """Search for opposing viewpoints and criticisms."""
        oppositions = []

        # Search for criticism of the main topic
        queries = [
            f"criticism of {topic}",
            f"{topic} limitations problems",
            f"{topic} alternatives better than",
        ]

        for query in queries[:2]:  # Limit to 2 searches
            results = await self.search_tool.search(query, max_results=3)
            for r in results:
                oppositions.append(f"[{r.title}] {r.snippet}")

        return oppositions

    async def _extract_claims(self, content: str) -> List[dict]:
        """Extract verifiable claims from content using LLM."""
        prompt = CLAIM_EXTRACTOR_PROMPT.format(content=content[:3000])

        messages = [
            HumanMessage(content=prompt),
        ]

        try:
            response = await self.llm.ainvoke(messages)
            text = response.content

            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start : end + 1]

            data = json.loads(text)
            return data.get("claims", [])

        except (json.JSONDecodeError, TypeError):
            return []

    async def _verify_single_claim(
        self,
        claim: str,
        claim_type: str,
        search_query: str,
    ) -> VerifiedClaim:
        """Verify a single claim via web search + LLM judgment."""
        try:
            results = await self.search_tool.search(search_query, max_results=3)

            if not results:
                return VerifiedClaim(
                    claim=claim,
                    status=VerificationStatus.UNVERIFIED,
                    notes="No search results found",
                )

            # Format search results for LLM
            results_text = "\n\n".join(
                f"Title: {r.title}\nURL: {r.url}\nSnippet: {r.snippet}"
                for r in results
            )

            prompt = VERIFY_PROMPT.format(
                claim=claim,
                claim_type=claim_type,
                search_results=results_text,
            )

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            text = response.content

            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start : end + 1]

            data = json.loads(text)

            return VerifiedClaim(
                claim=claim,
                status=VerificationStatus(data.get("status", "unverified")),
                source_url=data.get("source_url"),
                notes=data.get("notes", ""),
            )

        except Exception:
            return VerifiedClaim(
                claim=claim,
                status=VerificationStatus.UNVERIFIED,
                notes="Verification failed due to error",
            )
