"""State definitions for the thinking engine."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ThinkingPhase(str, Enum):
    """Phase of a thinking task within the 5-phase pipeline."""

    PENDING = "pending"
    ANCHORED = "anchored"        # Phase A complete
    GENERATED = "generated"      # Phase B complete
    CRITIQUED = "critiqued"      # Phase C complete (checkpoint 1)
    VERIFIED = "verified"        # Phase D complete (checkpoint 2)
    SYNTHESIZED = "synthesized"  # Phase E complete


class SessionStatus(str, Enum):
    """Overall session status."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class ThinkingDepth(str, Enum):
    """Depth of thinking analysis."""

    QUICK = "quick"              # 3-5 tasks, fast verification
    BALANCED = "balanced"        # 5-8 tasks, standard verification
    COMPREHENSIVE = "comprehensive"  # 8-15 tasks, deep verification


class VerificationStatus(str, Enum):
    """Status of a verified claim."""

    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    UNVERIFIED = "unverified"


class VerifiedClaim(BaseModel):
    """A single claim that has been fact-checked."""

    claim: str
    status: VerificationStatus
    source_url: Optional[str] = None
    notes: str = ""


class CritiquePoint(BaseModel):
    """A single point raised during adversarial critique."""

    severity: str = "medium"  # low, medium, high
    critique: str
    suggestion: str = ""


class CouncilPosition(BaseModel):
    """An expert's position in the council debate."""

    expert_name: str
    perspective: str
    position: str
    rebuttals: List[str] = Field(default_factory=list)


class ThinkingTask(BaseModel):
    """A single thinking task within a session."""

    id: str
    topic: str
    anchors: List[str] = Field(default_factory=list)
    phase: ThinkingPhase = ThinkingPhase.PENDING
    confidence: Optional[float] = None
    unverified_claims: List[str] = Field(default_factory=list)
    council_triggered: bool = False
    completed_at: Optional[datetime] = None

    # Phase outputs (populated as pipeline progresses)
    anchor_output: Optional[Dict[str, Any]] = None
    generation_output: Optional[str] = None
    critique_points: List[CritiquePoint] = Field(default_factory=list)
    council_positions: List[CouncilPosition] = Field(default_factory=list)
    verified_claims: List[VerifiedClaim] = Field(default_factory=list)
    synthesis: Optional[str] = None


class ThinkingSession(BaseModel):
    """A complete thinking session with all tasks and state."""

    session_id: str
    goal: str
    domain: str = "auto"
    depth: ThinkingDepth = ThinkingDepth.BALANCED
    status: SessionStatus = SessionStatus.ACTIVE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    tasks: List[ThinkingTask] = Field(default_factory=list)
    user_challenges: List[str] = Field(default_factory=list)

    def current_task(self) -> Optional[ThinkingTask]:
        """Get the first non-synthesized task."""
        for task in self.tasks:
            if task.phase != ThinkingPhase.SYNTHESIZED:
                return task
        return None

    def progress(self) -> tuple[int, int]:
        """Return (completed, total) task counts."""
        completed = sum(1 for t in self.tasks if t.phase == ThinkingPhase.SYNTHESIZED)
        return completed, len(self.tasks)

    def is_complete(self) -> bool:
        """Check if all tasks are synthesized."""
        return all(t.phase == ThinkingPhase.SYNTHESIZED for t in self.tasks) and len(self.tasks) > 0
