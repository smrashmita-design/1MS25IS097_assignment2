"""Tool registry: model-facing declarations plus validated execution."""

from __future__ import annotations

import logging
import time
from typing import Any

from google.genai import types
from pydantic import BaseModel, ValidationError

from app.tools.base import ToolError, ToolResult, ToolSpec

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Holds every tool the agent may invoke.

    The registry is the only place where model-provided arguments are turned
    into real side effects, which keeps validation in one auditable spot.
    """

    def __init__(self) -> None:
        self._specs: dict[str, ToolSpec] = {}
        self._validators: dict[str, type[BaseModel]] = {}
        self._cache: dict[str, ToolResult] = {}

    # ---------------------------------------------------------- registry --
    def register(self, spec: ToolSpec, validator: type[BaseModel] | None = None) -> None:
        self._specs[spec.name] = spec
        if validator is not None:
            self._validators[spec.name] = validator

    def get(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    def names(self) -> list[str]:
        return list(self._specs.keys())

    def declarations(self) -> list[types.Tool]:
        """Build the Gemini tool declarations for every registered tool."""
        return [spec.to_tool() for spec in self._specs.values()]

    # --------------------------------------------------------- validation --
    def validate(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Validate and normalise model supplied arguments."""
        validator = self._validators.get(name)
        if validator is None:
            return dict(args or {})
        try:
            model = validator.model_validate(args or {})
        except ValidationError as exc:
            details = "; ".join(
                f"{'.'.join(str(part) for part in err['loc']) or 'arguments'}: {err['msg']}"
                for err in exc.errors()
            )
            raise ToolError(
                f"Invalid arguments for tool '{name}': {details}",
                code="invalid_tool_arguments",
            ) from exc
        return model.model_dump(exclude_none=True)

    # ---------------------------------------------------------- execution --
    async def execute(self, name: str, args: dict[str, Any]) -> ToolResult:
        """Run a tool and always return a result (never raises for tool faults)."""
        spec = self._specs.get(name)
        if spec is None:
            return ToolResult(
                ok=False,
                error=f"Unknown tool '{name}'. Available tools: {', '.join(self._specs) or 'none'}.",
                display=f"Unknown tool `{name}`",
            )

        started = time.perf_counter()
        try:
            validated = self.validate(name, args)
        except ToolError as exc:
            return ToolResult(
                ok=False,
                error=exc.message,
                display=f"Invalid arguments for `{name}`",
                duration_ms=int((time.perf_counter() - started) * 1000),
            )

        try:
            result = await spec.handler(validated)
        except Exception as exc:  # noqa: BLE001 - tools must never crash the loop
            logger.exception("Tool %s failed", name)
            result = ToolResult(
                ok=False,
                error=f"{type(exc).__name__}: {exc}"[:400],
                display=f"`{name}` raised an error",
            )

        result.duration_ms = int((time.perf_counter() - started) * 1000)
        self._cache[name] = result
        return result

    # -------------------------------------------------------------- cache --
    def cached(self, name: str) -> ToolResult | None:
        return self._cache.get(name)
