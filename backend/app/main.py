"""NEXUS — FastAPI application entry point."""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import chat, conversations, health, settings as settings_routes
from app.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(name)s  %(message)s",
)
logger = logging.getLogger("nexus")

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Prepare shared resources on startup."""
    logger.info("%s v%s starting in %s mode", settings.app_name, settings.app_version, settings.environment)
    if not settings.gemini_configured:
        logger.warning(
            "GEMINI_API_KEY is not configured - the agent will return a configuration error. "
            "Copy backend/.env.example to backend/.env and add your key."
        )
    else:
        logger.info("Gemini configured with model '%s'", settings.gemini_model)
    logger.info("Search provider: %s", settings.search_provider)
    yield
    logger.info("NEXUS shutting down")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "A production-style ReAct agent: Gemini reasons, invokes a real web search "
        "tool, observes the results and iterates before answering."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Type", "X-Process-Time"],
)


@app.middleware("http")
async def timing_middleware(request: Request, call_next):
    """Attach a server-timing header to every response."""
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.perf_counter() - started) * 1000:.1f}ms"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return friendly validation errors instead of FastAPI's raw payload."""
    details = [
        {
            "field": ".".join(str(part) for part in error.get("loc", [])[1:]) or "body",
            "message": error.get("msg", "Invalid value"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
        content={
            "code": "validation_error",
            "message": "The request payload is invalid.",
            "details": details,
        },
    )


app.include_router(health.router, prefix="/api")
app.include_router(settings_routes.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Friendly landing payload."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/api/docs",
        "health": "/api/health",
    }
