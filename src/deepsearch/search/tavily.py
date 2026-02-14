"""Tavily search implementation."""

from typing import List

import httpx
from rich.console import Console

from deepsearch.search.base import SearchResult, SearchTool

TAVILY_API_URL = "https://api.tavily.com/search"

console = Console()


class TavilySearch(SearchTool):
    """Search tool using Tavily API."""

    def __init__(self, api_key: str, verbose: bool = True):
        super().__init__(api_key)
        self.verbose = verbose

    def get_name(self) -> str:
        return "tavily"

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute search via Tavily API."""
        if self.verbose:
            console.print(f"[dim]🔍 Searching: {query[:60]}...[/dim]")

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": False,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(TAVILY_API_URL, json=payload)
                response.raise_for_status()
                data = response.json()

            results = []
            for r in data.get("results", []):
                results.append(
                    SearchResult(
                        title=r.get("title", "Untitled"),
                        url=r.get("url", ""),
                        snippet=r.get("content", r.get("snippet", "")),
                        source=self._extract_source(r.get("url", "")),
                    )
                )

            if self.verbose:
                console.print(f"[green]   ✓ Found {len(results)} results[/green]")
                for r in results[:3]:
                    console.print(f"[dim]     • {r.title[:50]}... ({r.source})[/dim]")

            return results
        except Exception as e:
            if self.verbose:
                console.print(f"[red]   ✗ Search error: {e}[/red]")
            raise

    def _extract_source(self, url: str) -> str:
        """Extract source name from URL."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            domain = parsed.netloc.replace("www.", "")
            return domain.split(".")[0].capitalize()
        except:
            return ""
