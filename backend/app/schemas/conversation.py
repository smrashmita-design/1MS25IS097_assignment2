"""Conversation, message and saved-search models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Source(BaseModel):
    """A single citation attached to an assistant answer."""

    title: str
    url: str
    snippet: str = ""
    source: str = ""
    domain: str = ""
    rank: int = 0


class Message(BaseModel):
    """A single turn inside a conversation."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    role: Literal["user", "assistant"] = "user"
    content: str = ""
    created_at: datetime = Field(default_factory=_utcnow)
    sources: list[Source] = Field(default_factory=list)
    # The execution timeline for assistant turns (agent events).
    events: list[dict] = Field(default_factory=list)
    iterations: int = 0
    tool_calls: int = 0
    duration_ms: int = 0
    status: Literal["pending", "streaming", "complete", "error", "cancelled"] = "complete"
    error: str | None = None
    model: str = ""
    provider: str = ""


class Conversation(BaseModel):
    """A full conversation including its ReAct execution timelines."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "New research"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    messages: list[Message] = Field(default_factory=list)
    pinned: bool = False


class ConversationSummary(BaseModel):
    """Lightweight projection used by the sidebar list."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int
    preview: str = ""


class ConversationCreate(BaseModel):
    title: str | None = None


class RenameConversationRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)

    @field_validator("title")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("title must not be blank")
        return cleaned


class SavedSearch(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    query: str
    created_at: datetime = Field(default_factory=_utcnow)
    conversation_id: str | None = None
    run_count: int = 0


class SavedSearchCreate(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    conversation_id: str | None = None
