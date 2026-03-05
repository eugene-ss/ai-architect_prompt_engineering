"""Application settings, agent profiles, logging setup, constants."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.logging import RichHandler

VERSION_MAP: dict[str, str] = {
    "v1": "meta_prompts/tutor_v1_initial.md",
    "v2": "meta_prompts/tutor_v2_refined.md",
    "v3": "meta_prompts/tutor_v3_meta.md",
}

_PROFILES_DIR = Path(__file__).resolve().parents[2] / "profiles"

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    OPENAI_API_KEY: SecretStr = Field(
        ..., description="API key for the EPAM AI Proxy endpoint"
    )
    ENDPOINT_URL: str = Field(
        default="https://ai-proxy.lab.epam.com/",
        description="Base URL for the LLM proxy",
    )
    DEPLOYMENT_NAME: str = Field(
        default="gpt-4o-mini-2024-07-18",
        description="Azure OpenAI deployment / model name",
    )
    API_VERSION: str = Field(
        default="2025-01-01-preview",
        description="Azure OpenAI API version",
    )
    MAX_CONCURRENT_REQUESTS: int = Field(default=50, ge=1)
    REQUEST_TIMEOUT_SECONDS: float = Field(default=120.0, gt=0)
    LOG_LEVEL: str = Field(default="INFO")

    @property
    def completions_url(self) -> str:
        base = self.ENDPOINT_URL.rstrip("/")
        return (
            f"{base}/openai/deployments/{self.DEPLOYMENT_NAME}"
            f"/chat/completions?api-version={self.API_VERSION}"
        )

class LLMConfig(BaseModel):
    model: str = "gpt-4o-mini-2024-07-18"
    temperature: float = 0.3
    max_tokens: int = 4096

class AgentProfile(BaseModel):
    agent_name: str = "LanguageTutorReActAgent"
    max_turns: int = Field(default=10, ge=1)
    tool_budget: int = Field(default=8, ge=1)
    enable_self_reflection: bool = True
    system_prompt_file: str = "react_prompts/react_system.md"
    self_reflection_prompt_file: str = "react_prompts/self_reflection.md"
    llm_config: LLMConfig = Field(default_factory=LLMConfig)


def load_profile(name: str = "default") -> AgentProfile:
    """Load an agent profile by name from the ``profiles/`` directory."""
    path = _PROFILES_DIR / f"{name}.yaml"
    if not path.exists():
        logging.getLogger(__name__).warning(
            "Profile %s not found at %s – using defaults", name, path
        )
        return AgentProfile()
    raw: dict[str, Any] = (
        yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    )
    return AgentProfile(**raw)

def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[RichHandler(rich_tracebacks=True, show_time=True, show_path=False)],
        force=True,
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)