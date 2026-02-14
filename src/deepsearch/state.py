"""State definitions for the research workflow."""

from datetime import datetime
from enum import Enum
from typing import Annotated, List, Literal, Optional

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


class ResearchDepth(str, Enum):
    """Research depth levels."""

    QUICK = "quick"
    BALANCED = "balanced"
    COMPREHENSIVE = "comprehensive"


class ResearchStatus(str, Enum):
    """Research job status."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class SearchStrategy(str, Enum):
    """Search strategy based on content type."""

    GENERAL = "general"           # 通用搜索
    ACADEMIC = "academic"         # 学术论文 (arXiv, Google Scholar)
    NEWS = "news"                 # 新闻资讯
    TECHNICAL = "technical"       # 技术文档 (docs, GitHub)
    LEGAL = "legal"               # 法律法规
    FINANCIAL = "financial"       # 财经数据


class ResearchQuestion(BaseModel):
    """A research question in the plan with graph structure support."""

    # 基础字段
    id: str = Field(default_factory=lambda: f"q_{datetime.now().timestamp()}", description="Unique question ID")
    question: str = Field(description="The research question")
    priority: int = Field(default=1, description="Priority (1-5, higher is more important)")
    keywords: List[str] = Field(default_factory=list, description="Keywords for search")
    rationale: str = Field(default="", description="Why this question is important")

    # 图结构字段 - 支持分组和依赖
    category: str = Field(default="general", description="Question category/group (e.g., 'background', 'technical', 'comparison')")
    dependencies: List[str] = Field(default_factory=list, description="IDs of questions that must be answered before this one")
    order: int = Field(default=0, description="Execution order within category")

    # 搜索策略字段
    search_strategy: SearchStrategy = Field(default=SearchStrategy.GENERAL, description="Search strategy for this question")
    search_operators: List[str] = Field(default_factory=list, description="Additional search operators (e.g., 'site:arxiv.org', 'filetype:pdf')")


class Finding(BaseModel):
    """A single research finding."""

    question: str = Field(description="Which question this finding answers")
    source: str = Field(description="Source URL")
    title: str = Field(description="Source title")
    content: str = Field(description="Relevant content/snippet")
    credibility: float = Field(default=0.5, ge=0.0, le=1.0, description="Credibility score")
    timestamp: datetime = Field(default_factory=datetime.now)


class VerifiedFinding(BaseModel):
    """A finding that has been cross-verified."""

    finding: Finding
    verification_status: Literal["confirmed", "disputed", "unverified"]
    supporting_sources: List[str] = Field(default_factory=list)
    conflicting_sources: List[str] = Field(default_factory=list)
    notes: str = ""


class Conflict(BaseModel):
    """A conflict between findings."""

    finding_a: Finding
    finding_b: Finding
    conflict_description: str
    resolution: Optional[str] = None


class Section(BaseModel):
    """A section in the research report."""

    title: str
    content: str
    sources: List[str] = Field(default_factory=list)


class ReflectionResult(BaseModel):
    """Result of the reflection phase."""

    is_complete: bool = Field(description="Whether research is complete")
    gaps: List[str] = Field(default_factory=list, description="Knowledge gaps identified")
    new_questions: List[ResearchQuestion] = Field(default_factory=list)
    reasoning: str = ""


class SearchRecord(BaseModel):
    """Record of a search operation."""

    query: str
    provider: str
    results_count: int
    timestamp: datetime = Field(default_factory=datetime.now)


# LangGraph State
class ResearchState(TypedDict):
    """The main state for the research workflow."""

    # Job metadata
    job_id: str
    topic: str
    depth: ResearchDepth
    status: ResearchStatus

    # Planning
    plan: List[ResearchQuestion]
    current_question_index: int
    completed_question_ids: List[str]  # Track completed questions for dependency resolution

    # Research
    findings: Annotated[List[Finding], "append"]
    search_history: List[SearchRecord]

    # Reflection
    iteration: int
    max_iterations: int
    reflection: Optional[ReflectionResult]

    # Verification
    verified_findings: List[VerifiedFinding]
    conflicts: List[Conflict]

    # Output
    report: str
    report_sections: List[Section]

    # Error handling
    error: Optional[str]
