"""Tool abstractions for the agent's action space."""

from __future__ import annotations

import abc
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from google.genai import types


@dataclass(slots=True)
class ToolResult:
    """The outcome of a single tool execution."""

    ok: bool
    output: dict[str, Any] = field(default_factory=dict)
    display: str = ""
    error: str | None = None
    duration_ms: int = 0

    def to_model_payload(self) -> dict[str, Any]:
        """Shape returned to the model as the function response body."""
        if self.ok:
            return {"status": "ok", **self.output}
        return {"status": "error", "error": self.error or "Tool execution failed."}


@dataclass(slots=True)
class ToolSpec:
    """A callable tool plus its model-facing declaration."""

    name: str
    description: str
    parameters: types.Schema
    handler: Callable[[dict[str, Any]], Awaitable[ToolResult]]
    label: str = ""

    def declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=self.parameters,
        )

    def to_tool(self) -> types.Tool:
        return types.Tool(function_declarations=[self.declaration()])


class ToolError(RuntimeError):
    """Raised when a tool cannot be resolved or its arguments are invalid."""

    def __init__(self, message: str, *, code: str = "tool_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class Tool(abc.ABC):
    """Base class for tool implementations."""

    name: str = "tool"
    description: str = ""

    @abc.abstractmethod
    def spec(self) -> ToolSpec:
        """Return the concrete :class:`ToolSpec` for this tool."""
