"""Application configuration.

All runtime configuration is sourced from environment variables (12-factor).
Secrets are represented with :class:`pydantic.SecretStr` so they can never be
accidentally serialised into an API response or written to a log.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

SearchProviderName = Literal[
    "google_grounding",
    "duckduckgo",
    "serper",
    "tavily",
]


class Settings(BaseSettings):
    """Runtime settings for the NEXUS backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------------------------------------------------------------- app ---
    app_name: str = "NEXUS — ReAct Intelligence"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # -------------------------------------------------------------- llm ----
    gemini_api_key: SecretStr | None = Field(default=None)
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_version: str = "v1beta"
    llm_timeout_seconds: float = 120.0
    llm_max_output_tokens: int = 4096
    llm_temperature: float = 0.35

    # ------------------------------------------------------------ search ---
    search_provider: SearchProviderName = "google_grounding"
    serper_api_key: SecretStr | None = Field(default=None)
    tavily_api_key: SecretStr | None = Field(default=None)
    search_timeout_seconds: float = 30.0
    max_search_results: int = 8
    # How many grounding URLs we are willing to canonicalise (network cost).
    max_url_resolutions: int = 10

    # ------------------------------------------------------------ agent ---
    max_agent_iterations: int = 6
    agent_request_timeout_seconds: float = 180.0
    max_query_length: int = 4000
    max_history_messages: int = 12

    # ----------------------------------------------------------- server ----
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ]
    )
    cors_allow_credentials: bool = True

    # --------------------------------------------------------- storage ----
    store_dir: Path = Path("data")
    persistence_enabled: bool = True

    # --------------------------------------------------------- validators --
    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        """Allow ``A,B,C`` as well as a JSON array in ``.env`` files."""
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                return value
            return [item.strip() for item in raw.split(",") if item.strip()]
        return value

    # ---------------------------------------------------------- helpers ----
    @property
    def gemini_configured(self) -> bool:
        key = self.gemini_api_key
        return bool(key and key.get_secret_value().strip())

    @property
    def serper_configured(self) -> bool:
        key = self.serper_api_key
        return bool(key and key.get_secret_value().strip())

    @property
    def tavily_configured(self) -> bool:
        key = self.tavily_api_key
        return bool(key and key.get_secret_value().strip())

    @property
    def search_provider_configured(self) -> bool:
        """Is the *selected* search provider usable with the current secrets?"""
        match self.search_provider:
            case "google_grounding":
                return self.gemini_configured
            case "serper":
                return self.serper_configured
            case "tavily":
                return self.tavily_configured
            case "duckduckgo":
                return True
        return False


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear the cached settings (used by tests that patch the environment)."""
    get_settings.cache_clear()
