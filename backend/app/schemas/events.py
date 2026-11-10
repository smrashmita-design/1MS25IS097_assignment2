"""Structured agent execution events (the SSE contract)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AgentEventType(str, Enum):
    """Every event the agent loop can emit over the wire."""

    AGENT_STARTED = "agent_started"
    PLANNING = "planning"
    TOOL_SELECTED = "tool_selected"
    TOOL_CALL = "tool_call"
    TOOL_STARTED = "tool_started"
    TOOL_RESULT = "tool_result"
    OBSERVATION = "observation"
    TOKEN = "token"
    FINAL_ANSWER = "final_answer"
    AGENT_COMPLETED = "agent_completed"
    AGENT_ERROR = "agent_error"
    AGENT_CANCELLED = "agent_cancelled"


class AgentEvent(BaseModel):
    """A single, uniformly shaped execution event.

    The frontend timeline is driven entirely by these payloads, therefore every
    event uses the exact same envelope: ``id`` / ``type`` / ``timestamp`` /
    ``step`` / ``title`` / ``detail`` / ``data``.
    """

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    type: AgentEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    step: int = 0
    title: str = ""
    detail: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    def to_sse(self) -> str:
        """Serialise the event into a Server-Sent Events frame."""
        payload = self.model_dump_json()
        return f"id: {self.id}\nevent: {self.type.value}\ndata: {payload}\n\n"
