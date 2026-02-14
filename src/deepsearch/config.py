"""Configuration management for DeepSearch."""

import os
from pathlib import Path
from typing import Literal, Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SearchConfig(BaseSettings):
    """Search provider configuration."""

    provider: Literal["openrouter", "tavily"] = "openrouter"
    model: str = "openai/gpt-4o-mini"  # Model to use for OpenRouter search enhancement
    max_results: int = 5
    timeout: int = 30


class LLMConfig(BaseSettings):
    """LLM configuration."""

    provider: Literal["openrouter", "openai", "anthropic"] = "openrouter"
    model: str = "openai/gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 4096


class ResearchDefaults(BaseSettings):
    """Default research settings."""

    depth: Literal["quick", "balanced", "comprehensive"] = "balanced"
    max_iterations: int = 5
    output_format: Literal["markdown", "json", "pdf"] = "markdown"


class StorageConfig(BaseSettings):
    """Storage configuration."""

    db_path: Optional[Path] = None

    def get_db_path(self) -> Path:
        if self.db_path:
            return self.db_path
        # Default location
        if os.name == "nt":  # Windows
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:  # Linux/macOS
            base = Path.home() / ".local" / "share"
        path = base / "deepsearch" / "research.db"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


class Config(BaseSettings):
    """Main configuration."""

    model_config = SettingsConfigDict(
        env_prefix="DEEPSEARCH_",
        env_nested_delimiter="__",
        yaml_file="~/.config/deepsearch/config.yaml",
        extra="ignore",  # Allow extra fields from YAML for backward compatibility
    )

    # API Keys
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    tavily_api_key: Optional[str] = Field(default=None, alias="TAVILY_API_KEY")
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Sub-configs
    search: SearchConfig = Field(default_factory=SearchConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    defaults: ResearchDefaults = Field(default_factory=ResearchDefaults)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    @classmethod
    def load(cls) -> "Config":
        """Load configuration from file and environment."""
        config_file = Path.home() / ".config" / "deepsearch" / "config.yaml"

        # Start with defaults
        config = cls()

        # Load from YAML if exists
        if config_file.exists():
            with open(config_file) as f:
                data = yaml.safe_load(f) or {}
                # Extract API keys from YAML (may be at top level)
                api_keys = {
                    "openrouter_api_key": data.pop("openrouter_api_key", None),
                    "tavily_api_key": data.pop("tavily_api_key", None),
                    "openai_api_key": data.pop("openai_api_key", None),
                    "anthropic_api_key": data.pop("anthropic_api_key", None),
                }
                # Load nested config
                config = cls(**data)
                # Set API keys from YAML if present
                for key, value in api_keys.items():
                    if value:
                        setattr(config, key, value)

        # Environment variables override
        config.openrouter_api_key = os.getenv(
            "OPENROUTER_API_KEY", config.openrouter_api_key
        )
        config.tavily_api_key = os.getenv("TAVILY_API_KEY", config.tavily_api_key)
        config.openai_api_key = os.getenv("OPENAI_API_KEY", config.openai_api_key)
        config.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", config.anthropic_api_key)

        return config

    def save(self) -> None:
        """Save configuration to file."""
        config_file = Path.home() / ".config" / "deepsearch" / "config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "openrouter_api_key": self.openrouter_api_key,
            "tavily_api_key": self.tavily_api_key,
            "search": {
                "provider": self.search.provider,
                "model": self.search.model,
                "max_results": self.search.max_results,
            },
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
            },
            "defaults": {
                "depth": self.defaults.depth,
                "max_iterations": self.defaults.max_iterations,
            },
        }

        with open(config_file, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def get_search_api_key(self) -> Optional[str]:
        """Get the API key for the configured search provider."""
        if self.search.provider == "openrouter":
            return self.openrouter_api_key
        elif self.search.provider == "tavily":
            return self.tavily_api_key
        return None

    def get_llm_api_key(self) -> Optional[str]:
        """Get the API key for the configured LLM provider."""
        if self.llm.provider == "openrouter":
            return self.openrouter_api_key
        elif self.llm.provider == "openai":
            return self.openai_api_key
        elif self.llm.provider == "anthropic":
            return self.anthropic_api_key
        return None
