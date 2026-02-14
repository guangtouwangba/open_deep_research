"""State persistence using SQLite."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import aiosqlite

from deepsearch.state import (
    Conflict,
    Finding,
    ReflectionResult,
    ResearchQuestion,
    ResearchState,
    ResearchStatus,
    SearchRecord,
    Section,
    VerifiedFinding,
)


class Storage:
    """SQLite storage for research jobs."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init(self):
        """Initialize database tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS research_jobs (
                    id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    depth TEXT NOT NULL,
                    status TEXT NOT NULL,
                    plan_json TEXT,
                    current_question_index INTEGER DEFAULT 0,
                    findings_json TEXT,
                    search_history_json TEXT,
                    iteration INTEGER DEFAULT 0,
                    max_iterations INTEGER DEFAULT 5,
                    reflection_json TEXT,
                    verified_findings_json TEXT,
                    conflicts_json TEXT,
                    report TEXT,
                    report_sections_json TEXT,
                    error TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            await db.commit()

    async def create_job(
        self,
        topic: str,
        depth: str,
        max_iterations: int = 5,
    ) -> str:
        """Create a new research job."""
        job_id = str(uuid.uuid4())[:8]

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO research_jobs
                (id, topic, depth, status, max_iterations)
                VALUES (?, ?, ?, ?, ?)
                """,
                (job_id, topic, depth, ResearchStatus.PENDING.value, max_iterations),
            )
            await db.commit()

        return job_id

    async def save_state(self, state: ResearchState) -> None:
        """Save research state."""
        # Helper to safely serialize objects that may be Pydantic models or dicts
        def serialize_item(item):
            if hasattr(item, "model_dump"):
                return item.model_dump(mode="json")  # mode="json" handles datetime
            elif isinstance(item, dict):
                # Recursively handle datetime in dicts
                return {k: serialize_value(v) for k, v in item.items()}
            else:
                return serialize_value(item)

        def serialize_value(v):
            """Serialize a single value, handling datetime and other types."""
            from datetime import datetime as dt
            if isinstance(v, dt):
                return v.isoformat()
            elif isinstance(v, dict):
                return {k: serialize_value(val) for k, val in v.items()}
            elif isinstance(v, list):
                return [serialize_value(i) for i in v]
            elif hasattr(v, "model_dump"):
                return v.model_dump(mode="json")
            else:
                return v

        def serialize_list(items):
            if not items:
                return "[]"
            return json.dumps([serialize_item(i) for i in items])

        # Get status value safely
        status = state.get("status", ResearchStatus.RUNNING)
        status_value = status.value if hasattr(status, "value") else str(status)

        # Serialize reflection if present
        reflection = state.get("reflection")
        reflection_json = None
        if reflection:
            reflection_json = json.dumps(serialize_item(reflection))

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE research_jobs SET
                    status = ?,
                    plan_json = ?,
                    current_question_index = ?,
                    findings_json = ?,
                    search_history_json = ?,
                    iteration = ?,
                    reflection_json = ?,
                    verified_findings_json = ?,
                    conflicts_json = ?,
                    report = ?,
                    report_sections_json = ?,
                    error = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    status_value,
                    serialize_list(state.get("plan", [])),
                    state.get("current_question_index", 0),
                    serialize_list(state.get("findings", [])),
                    serialize_list(state.get("search_history", [])),
                    state.get("iteration", 0),
                    reflection_json,
                    serialize_list(state.get("verified_findings", [])),
                    serialize_list(state.get("conflicts", [])),
                    state.get("report"),
                    serialize_list(state.get("report_sections", [])),
                    state.get("error"),
                    state["job_id"],
                ),
            )
            await db.commit()

    async def load_state(self, job_id: str) -> Optional[ResearchState]:
        """Load research state."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM research_jobs WHERE id = ?", (job_id,)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return None

        return self._row_to_state(row)

    async def list_jobs(self, limit: int = 10) -> List[dict]:
        """List recent research jobs."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT id, topic, depth, status, created_at, updated_at
                FROM research_jobs
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()

        return [dict(row) for row in rows]

    async def update_status(self, job_id: str, status: ResearchStatus) -> None:
        """Update job status."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE research_jobs SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status.value, job_id),
            )
            await db.commit()

    def _row_to_state(self, row: aiosqlite.Row) -> ResearchState:
        """Convert database row to ResearchState."""
        return ResearchState(
            job_id=row["id"],
            topic=row["topic"],
            depth=row["depth"],
            status=ResearchStatus(row["status"]),
            plan=[ResearchQuestion(**q) for q in json.loads(row["plan_json"] or "[]")],
            current_question_index=row["current_question_index"],
            findings=[Finding(**f) for f in json.loads(row["findings_json"] or "[]")],
            search_history=[SearchRecord(**s) for s in json.loads(row["search_history_json"] or "[]")],
            iteration=row["iteration"],
            max_iterations=row["max_iterations"],
            reflection=ReflectionResult(**json.loads(row["reflection_json"])) if row["reflection_json"] else None,
            verified_findings=[VerifiedFinding(**v) for v in json.loads(row["verified_findings_json"] or "[]")],
            conflicts=[Conflict(**c) for c in json.loads(row["conflicts_json"] or "[]")],
            report=row["report"],
            report_sections=[Section(**s) for s in json.loads(row["report_sections_json"] or "[]")],
            error=row["error"],
        )
