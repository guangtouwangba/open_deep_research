"""Domain plugin base class and registry."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Expert:
    """An expert persona for council debates."""

    name: str
    perspective: str
    anchor_source: str  # The authority this expert draws from
    style: str = ""     # e.g., "aggressive", "cautious", "practical"


@dataclass
class DomainPlugin:
    """Base class for domain-specific thinking configurations."""

    name: str
    display_name: str
    detection_keywords: List[str]
    authority_sources: Dict[str, List[str]]  # sub-topic → [authority sources]
    anchor_templates: List[str]
    verification_rules: List[str]
    council_experts: List[Expert]
    downstream_skills: List[str] = field(default_factory=list)
    multi_school_topics: List[str] = field(default_factory=list)  # Topics that always trigger council

    def get_anchors_for_topic(self, topic: str) -> List[str]:
        """Find relevant authority sources for a given topic."""
        topic_lower = topic.lower()
        relevant = []
        for sub_topic, sources in self.authority_sources.items():
            if any(kw in topic_lower for kw in sub_topic.lower().split()):
                relevant.extend(sources)
        # Fallback: return first category's sources
        if not relevant and self.authority_sources:
            first_key = next(iter(self.authority_sources))
            relevant = self.authority_sources[first_key]
        return relevant

    def should_trigger_council(self, topic: str) -> bool:
        """Check if this topic inherently requires multi-perspective analysis."""
        topic_lower = topic.lower()
        return any(kw in topic_lower for kw in self.multi_school_topics)

    def format_anchor_prompt(self, topic: str, sources: List[str]) -> str:
        """Format an anchoring prompt using templates and sources."""
        if not self.anchor_templates or not sources:
            return topic

        template = self.anchor_templates[0]
        sources_str = ", ".join(sources[:3])
        return template.format(topic=topic, sources=sources_str, source=sources[0])


# --- Domain Registry ---

_REGISTRY: Dict[str, DomainPlugin] = {}


def register_domain(plugin: DomainPlugin) -> None:
    """Register a domain plugin."""
    _REGISTRY[plugin.name] = plugin


def get_domain(name: str) -> Optional[DomainPlugin]:
    """Get a domain plugin by name."""
    _ensure_loaded()
    return _REGISTRY.get(name)


def list_domains() -> List[DomainPlugin]:
    """List all registered domain plugins."""
    _ensure_loaded()
    return list(_REGISTRY.values())


def detect_domain(goal: str) -> Optional[DomainPlugin]:
    """Auto-detect the best domain for a given goal."""
    _ensure_loaded()
    goal_lower = goal.lower()

    best_match = None
    best_score = 0

    for plugin in _REGISTRY.values():
        score = sum(1 for kw in plugin.detection_keywords if kw in goal_lower)
        if score > best_score:
            best_score = score
            best_match = plugin

    return best_match


def _ensure_loaded() -> None:
    """Lazy-load all domain plugins."""
    if _REGISTRY:
        return

    # Import all domain modules to trigger registration
    from deep_thinking.domains import (  # noqa: F401
        content_creation,
        game_dev,
        investment,
        learning,
        research,
        tech_eval,
    )
