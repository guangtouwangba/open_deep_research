"""Base class for search tools."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class SearchResult:
    """A single search result."""

    title: str
    url: str
    snippet: str
    source: str = ""  # Website name


class SearchTool(ABC):
    """Abstract base class for search tools."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute a search query.

        Args:
            query: The search query
            max_results: Maximum number of results to return

        Returns:
            List of search results
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of the search provider."""
        pass
