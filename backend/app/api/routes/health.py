"""Health and connectivity endpoints."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.agent.controller import AgentController
from app.api.deps import get_app_settings, get_controller
from app.config import Settings
from app.schemas.status import ComponentStatus, HealthResponse, StatusResponse

router = APIRouter(tags=["system"])

_STARTED_AT = time.time()


@router.get("/health", response_model=HealthResponse)
async def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    """Liveness probe used by Render/Vercel and the frontend status pill."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(time.time() - _STARTED_AT, 2),
    )


@router.get("/status", response_model=StatusResponse)
async def status(
    settings: Settings = Depends(get_app_settings),
    controller: AgentController = Depends(get_controller),
) -> StatusResponse:
    """Report live connectivity for the LLM and the search provider."""
    llm_ok, llm_detail = await controller.llm.ping()
    llm_status = ComponentStatus(
        name="Google Gemini",
        configured=settings.gemini_configured,
        connected=llm_ok,
        detail=llm_detail,
    )

    search_ok, search_detail = await controller.search_provider.health()
    search_status = ComponentStatus(
        name=controller.search_provider.label,
        configured=settings.search_provider_configured,
        connected=search_ok,
        detail=search_detail,
    )

    overall = "operational" if llm_ok and search_ok else "degraded"
    return StatusResponse(
        status=overall,
        llm=llm_status,
        search=search_status,
        model=settings.gemini_model,
        search_provider=controller.search_provider.name,
        max_iterations=settings.max_agent_iterations,
        max_search_results=settings.max_search_results,
        checked_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/models")
async def models(
    settings: Settings = Depends(get_app_settings),
    controller: AgentController = Depends(get_controller),
) -> dict[str, object]:
    """List the Gemini models reachable with the configured credentials."""
    try:
        available = await controller.llm.list_models()
    except Exception as exc:  # noqa: BLE001
        return {"model": settings.gemini_model, "available": [], "error": str(exc)[:200]}
    preferred = [m for m in available if m.startswith(settings.gemini_model.split("-")[0])]
    return {
        "model": settings.gemini_model,
        "available": available[:80],
        "recommended": preferred[:20],
    }
