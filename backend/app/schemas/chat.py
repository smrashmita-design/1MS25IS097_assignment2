"""Request/response models for the chat endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.schemas.conversation import Source


class ChatRequest(BaseModel):
    """Payload accepted by ``POST /api/chat/stream``."""

    message: str = Field(..., min_length=1, description="The user's research query.")
    conversation_id: str | None = Field(
        default=None, description="Existing conversation to append the turn to."
    )
    run_id: str | None = Field(
        default=None, description="Client supplied id, echoed back on every event."
    )
    max_iterations: int | None = Field(
        default=None, ge=1, le=12, description="Override the server iteration budget."
    )
    save_search: bool = Field(
        default=False, description="Persist this query as a saved search."
    )

    @field_validator("message")
    @classmethod
    def _strip(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message must not be blank")
        return cleaned

    @field_validator("message")
    @classmethod
    def _length_guard(cls, value: str) -> str:
        if len(value) > 8000:
            raise ValueError("message exceeds the maximum accepted length")
        return value


class ChatResponse(BaseModel):
    """Non-streaming summary returned when a run is rejected or completed early."""

    run_id: str
    conversation_id: str
    content: str = ""
    sources: list[Source] = Field(default_factory=list)
    iterations: int = 0
    tool_calls: int = 0
    duration_ms: int = 0


class StopRequest(BaseModel):
    """Payload for ``POST /api/chat/stop``."""

    run_id: str


class StopResponse(BaseModel):
    run_id: str
    stopped: bool
    detail: str


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
