"""Session management — CRUD operations and file-based state persistence."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from deep_thinking.config import SESSIONS_DIR, ensure_state_dir
from deep_thinking.state import (
    SessionStatus,
    ThinkingPhase,
    ThinkingSession,
    ThinkingTask,
)


def _slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    # Keep Chinese characters and alphanumeric
    text = text.lower().strip()
    text = re.sub(r"[^\w\u4e00-\u9fff\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = text[:50].rstrip("-")
    return text


def create_session(goal: str, domain: str = "auto", depth: str = "balanced") -> ThinkingSession:
    """Create a new thinking session with directory and template files."""
    ensure_state_dir()

    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = _slugify(goal)
    session_id = f"{date_str}-{slug}"

    # Ensure unique session_id
    session_dir = SESSIONS_DIR / session_id
    counter = 1
    while session_dir.exists():
        session_id = f"{date_str}-{slug}-{counter}"
        session_dir = SESSIONS_DIR / session_id
        counter += 1

    session_dir.mkdir(parents=True)

    session = ThinkingSession(
        session_id=session_id,
        goal=goal,
        domain=domain,
        depth=depth,
    )

    # Write initial files
    _save_progress(session)
    _save_findings(session)
    _save_sources(session)

    return session


def load_session(session_id: str) -> Optional[ThinkingSession]:
    """Load a session from disk."""
    progress_file = SESSIONS_DIR / session_id / "thinking-progress.json"
    if not progress_file.exists():
        return None

    with open(progress_file) as f:
        data = json.load(f)

    return ThinkingSession(**data)


def save_session(session: ThinkingSession) -> None:
    """Save session state to disk."""
    session.updated_at = datetime.now()
    _save_progress(session)


def list_sessions() -> List[dict]:
    """List all sessions with summary info."""
    ensure_state_dir()
    sessions = []

    for session_dir in sorted(SESSIONS_DIR.iterdir(), reverse=True):
        if not session_dir.is_dir():
            continue
        progress_file = session_dir / "thinking-progress.json"
        if not progress_file.exists():
            continue

        with open(progress_file) as f:
            data = json.load(f)

        tasks = data.get("tasks", [])
        completed = sum(1 for t in tasks if t.get("phase") == ThinkingPhase.SYNTHESIZED.value)

        sessions.append({
            "session_id": data["session_id"],
            "goal": data["goal"],
            "domain": data.get("domain", "auto"),
            "status": data.get("status", "active"),
            "tasks_completed": completed,
            "tasks_total": len(tasks),
            "updated_at": data.get("updated_at", ""),
        })

    return sessions


def append_finding(session: ThinkingSession, task: ThinkingTask, content: str) -> None:
    """Append a completed task's findings to findings.md."""
    session_dir = SESSIONS_DIR / session.session_id
    findings_file = session_dir / "findings.md"

    phase_label = task.phase.value.upper()
    confidence_str = f" confidence: {task.confidence}" if task.confidence else ""
    status_icon = "✅" if task.phase == ThinkingPhase.SYNTHESIZED else "🔄"

    entry = f"\n\n## {task.id}: {task.topic} [{phase_label} {status_icon}{confidence_str}]\n\n"

    if task.anchors:
        entry += "### 权威源\n"
        for anchor in task.anchors:
            entry += f"- {anchor}\n"
        entry += "\n"

    entry += f"### 核心结论\n{task.synthesis or task.generation_output or ''}\n\n"

    if task.critique_points:
        entry += "### 红军批判\n"
        for cp in task.critique_points:
            entry += f"- 🔴 [{cp.severity}] {cp.critique}\n"
        entry += "\n"

    if task.verified_claims:
        entry += "### 验证结果\n"
        for vc in task.verified_claims:
            icon = {"confirmed": "✅", "disputed": "❌", "unverified": "⚠️"}[vc.status.value]
            entry += f"- {icon} {vc.claim}"
            if vc.source_url:
                entry += f" — {vc.source_url}"
            entry += "\n"
        entry += "\n"

    if task.council_positions:
        entry += "### 专家委员会\n"
        for pos in task.council_positions:
            entry += f"**{pos.expert_name}** ({pos.perspective}):\n{pos.position}\n\n"

    with open(findings_file, "a", encoding="utf-8") as f:
        f.write(entry)


def add_verified_source(session: ThinkingSession, source: str, source_type: str, url: str) -> None:
    """Add a verified source to sources.md."""
    session_dir = SESSIONS_DIR / session.session_id
    sources_file = session_dir / "sources.md"

    date_str = datetime.now().strftime("%Y-%m-%d")
    line = f"| {source} | {source_type} | ✅ {date_str} | {url} |\n"

    with open(sources_file, "a", encoding="utf-8") as f:
        f.write(line)


# --- Internal helpers ---

def _save_progress(session: ThinkingSession) -> None:
    """Write thinking-progress.json."""
    session_dir = SESSIONS_DIR / session.session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    progress_file = session_dir / "thinking-progress.json"

    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(
            session.model_dump(mode="json"),
            f,
            indent=2,
            ensure_ascii=False,
        )


def _save_findings(session: ThinkingSession) -> None:
    """Write initial findings.md."""
    session_dir = SESSIONS_DIR / session.session_id
    findings_file = session_dir / "findings.md"
    if not findings_file.exists():
        with open(findings_file, "w", encoding="utf-8") as f:
            f.write(f"# Findings: {session.goal}\n")


def _save_sources(session: ThinkingSession) -> None:
    """Write initial sources.md."""
    session_dir = SESSIONS_DIR / session.session_id
    sources_file = session_dir / "sources.md"
    if not sources_file.exists():
        with open(sources_file, "w", encoding="utf-8") as f:
            f.write("# Verified Sources\n\n")
            f.write("| Source | Type | Verified | URL |\n")
            f.write("|--------|------|----------|-----|\n")
