"""Configuration management for Deep Thinking Engine."""

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


STATE_DIR = Path.home() / ".thinking-agent"
SESSIONS_DIR = STATE_DIR / "sessions"
CONFIG_PATH = STATE_DIR / "config.json"


class ThinkingConfig(BaseModel):
    """Configuration for the thinking engine."""

    default_depth: str = "balanced"
    default_domain: str = "auto"
    language: str = "zh"
    checkpoints: bool = True
    council_auto_trigger: bool = True
    council_confidence_threshold: float = 0.5
    max_tasks: int = 15

    @classmethod
    def load(cls) -> "ThinkingConfig":
        """Load config from ~/.thinking-agent/config.json."""
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                data = json.load(f)
            return cls(**data)
        return cls()

    def save(self) -> None:
        """Save config to disk."""
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.model_dump(), f, indent=2, ensure_ascii=False)


def ensure_state_dir() -> None:
    """Ensure the global state directory exists."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        ThinkingConfig().save()
