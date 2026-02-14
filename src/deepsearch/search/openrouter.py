"""OpenRouter search implementation with LLM-enhanced queries."""

import asyncio
import json
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from rich.console import Console

from deepsearch.search.base import SearchResult, SearchTool

console = Console()

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterSearch(SearchTool):
    """Search tool using OpenRouter LLM for query enhancement + DuckDuckGo for search."""

    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini", verbose: bool = True):
        """Initialize search with OpenRouter API key and model for query enhancement."""
        super().__init__(api_key)
        self.model = model
        self.verbose = verbose

    def get_name(self) -> str:
        return "openrouter"

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute search with LLM-enhanced query."""
        if self.verbose:
            console.print(f"[dim]🔍 Original query: {query[:60]}...[/dim]")

        # Enhance query using LLM
        enhanced_queries = await self._enhance_query(query)

        if self.verbose:
            console.print(f"[dim]   Enhanced to {len(enhanced_queries)} search queries[/dim]")

        # Execute searches
        all_results = []
        for eq in enhanced_queries[:2]:  # Limit to 2 queries
            if self.verbose:
                console.print(f"[dim]   → Searching: {eq[:50]}...[/dim]")

            results = await self._execute_search(eq, max_results)
            all_results.extend(results)

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                unique_results.append(r)

        if self.verbose:
            console.print(f"[green]   ✓ Found {len(unique_results)} unique results[/green]")
            for r in unique_results[:3]:
                console.print(f"[dim]     • {r.title[:50]}... ({r.source})[/dim]")

        return unique_results[:max_results]

    async def _enhance_query(self, query: str) -> List[str]:
        """Use LLM to generate better search queries."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/deepsearch-cli",
                "X-Title": "DeepSearch CLI",
            }

            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a search query optimizer. Given a research question, generate 2-3 effective search queries that will find relevant information. Return ONLY a JSON array of strings, no explanation.",
                    },
                    {
                        "role": "user",
                        "content": f"Generate search queries for: {query}",
                    },
                ],
                "temperature": 0.3,
                "max_tokens": 200,
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(OPENROUTER_API_URL, headers=headers, json=payload)
                if response.status_code != 200:
                    if self.verbose:
                        console.print(f"[yellow]   ⚠ LLM enhancement failed, using original query[/yellow]")
                    return [query]

                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                # Parse JSON array from response
                start = content.find("[")
                end = content.rfind("]")
                if start != -1 and end != -1:
                    queries = json.loads(content[start:end + 1])
                    return queries if queries else [query]

                return [query]

        except Exception as e:
            if self.verbose:
                console.print(f"[yellow]   ⚠ Query enhancement error: {e}[/yellow]")
            return [query]

    async def _execute_search(self, query: str, max_results: int) -> List[SearchResult]:
        """Execute search using DuckDuckGo."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, query, max_results)

    def _sync_search(self, query: str, max_results: int) -> List[SearchResult]:
        """Synchronous search using duckduckgo-search library."""
        try:
            from duckduckgo_search import DDGS

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(
                        SearchResult(
                            title=r.get("title", "Untitled"),
                            url=r.get("href", r.get("link", "")),
                            snippet=r.get("body", r.get("snippet", "")),
                            source=self._extract_source(r.get("href", "")),
                        )
                    )
            return results
        except Exception as e:
            if self.verbose:
                console.print(f"[red]   ✗ DuckDuckGo error: {e}[/red]")
            return []

    def _extract_source(self, url: str) -> str:
        """Extract source name from URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain.split(".")[0].capitalize()
        except:
            return ""
