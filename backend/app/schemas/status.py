"""Health, status and settings payloads."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"] = "ok"
    app: str
    version: str
    environment: str
    uptime_seconds: float


class ComponentStatus(BaseModel):
    name: str
    configured: bool
    connected: bool = False
    detail: str = ""
    latency_ms: int | None = None


class StatusResponse(BaseModel):
    status: str
    llm: ComponentStatus
    search: ComponentStatus
    model: str
    search_provider: str
    max_iterations: int
    max_search_results: int
    checked_at: str


class SettingsResponse(BaseModel):
    """A sanitised view of the configuration — never contains secrets."""

    app_name: str
    app_version: str
    environment: str
    model: str
    search_provider: str
    search_providers_available: list[str]
    max_agent_iterations: int
    max_search_results: int
    llm_timeout_seconds: float
    agent_request_timeout_seconds: float
    theme_options: list[str]
    feature_flags: dict[str, Any] = Field(default_factory=dict)
