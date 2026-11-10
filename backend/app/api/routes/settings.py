"""Sanitised settings endpoint.

The backend never exposes secrets — only whether they are configured.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_app_settings
from app.config import Settings
from app.schemas.status import SettingsResponse
from app.search.factory import AVAILABLE_PROVIDERS

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsResponse)
async def read_settings(settings: Settings = Depends(get_app_settings)) -> SettingsResponse:
    """Return the runtime configuration with every secret redacted."""
    return SettingsResponse(
        app_name=settings.app_name,
        app_version=settings.app_version,
        environment=settings.environment,
        model=settings.gemini_model,
        search_provider=settings.search_provider,
        search_providers_available=list(AVAILABLE_PROVIDERS),
        max_agent_iterations=settings.max_agent_iterations,
        max_search_results=settings.max_search_results,
        llm_timeout_seconds=settings.llm_timeout_seconds,
        agent_request_timeout_seconds=settings.agent_request_timeout_seconds,
        theme_options=["dark", "light", "system"],
        feature_flags={
            "gemini_configured": settings.gemini_configured,
            "serper_configured": settings.serper_configured,
            "tavily_configured": settings.tavily_configured,
            "search_provider_configured": settings.search_provider_configured,
            "persistence_enabled": settings.persistence_enabled,
        },
    )
