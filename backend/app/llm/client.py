"""Abstract LLM client contract used by the ReAct loop."""

from __future__ import annotations

import abc
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import Any

from google.genai import types


class LLMError(RuntimeError):
    """Raised when the model backend fails (auth, quota, timeout, transport)."""

    def __init__(self, message: str, *, code: str = "llm_error", recoverable: bool = True) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.recoverable = recoverable


@dataclass(slots=True)
class ToolCall:
    """A function call requested by the model."""

    id: str
    name: str
    args: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ModelTurn:
    """One assistant turn: optional text, optional tool calls, optional grounding."""

    text: str = ""
    function_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str = ""
    grounding_metadata: Any | None = None
    parts: list[Any] = field(default_factory=list)

    @property
    def has_function_calls(self) -> bool:
        return bool(self.function_calls)


class LLMClient(abc.ABC):
    """Contract every chat-model backend must satisfy."""

    model: str = "unknown"

    @abc.abstractmethod
    def build_tools(self) -> list[types.Tool]:
        """Return the tool declarations advertised to the model."""

    @abc.abstractmethod
    async def stream_turn(
        self,
        contents: Sequence[types.Content],
        *,
        tools: list[types.Tool],
        system_instruction: str,
    ) -> AsyncIterator[ModelTurn]:
        """Yield incremental assistant turns for a single round-trip."""

    @abc.abstractmethod
    async def generate(
        self,
        contents: Sequence[types.Content] | str,
        *,
        tools: list[types.Tool] | None = None,
        system_instruction: str | None = None,
    ) -> ModelTurn:
        """Execute a single, non-streaming completion."""

    @abc.abstractmethod
    async def list_models(self) -> list[str]:
        """Return the model ids available to the current credentials."""

    @abc.abstractmethod
    async def ping(self) -> tuple[bool, str]:
        """Return ``(reachable, detail)`` for the status endpoint."""
