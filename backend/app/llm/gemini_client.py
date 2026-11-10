"""Concrete :class:`LLMClient` implementation backed by Google Gemini.

Uses the official ``google-genai`` SDK with the ``v1beta`` API surface, which is
required for Gemini's function-calling (tool use) support.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator, Sequence
from typing import Any

from google import genai
from google.genai import types

from app.config import Settings, get_settings
from app.llm.client import LLMClient, LLMError, ModelTurn, ToolCall

logger = logging.getLogger(__name__)

# Transient upstream failures (503 UNAVAILABLE / 429) are retried with backoff.
_MAX_ATTEMPTS = 4
_RETRY_BASE_DELAY = 2.0


def _extract_function_calls(candidate: Any) -> list[ToolCall]:
    """Pull every function call out of a candidate's parts."""
    calls: list[ToolCall] = []
    for part in _extract_parts(candidate):
        function_call = getattr(part, "function_call", None)
        if function_call is None:
            continue
        name = getattr(function_call, "name", None)
        if not name:
            continue
        raw_args = getattr(function_call, "args", None) or {}
        args = dict(raw_args) if isinstance(raw_args, dict) else {}
        calls.append(
            ToolCall(
                id=getattr(function_call, "id", None) or uuid.uuid4().hex,
                name=name,
                args=args,
            )
        )
    return calls


def _extract_parts(candidate: Any) -> list[Any]:
    """Return the raw parts of a candidate.

    The raw parts must be replayed verbatim on the next turn: Gemini 3.x
    models reject a function call that is missing its ``thought_signature``.
    """
    content = getattr(candidate, "content", None)
    if content is None:
        return []
    return list(getattr(content, "parts", None) or [])


class GeminiClient(LLMClient):
    """Thin, well-behaved wrapper around ``google.genai``."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.model = self.settings.gemini_model
        self._client: genai.Client | None = None

    # ------------------------------------------------------------ helpers --
    @property
    def is_configured(self) -> bool:
        return self.settings.gemini_configured

    def _require_key(self) -> str:
        key = self.settings.gemini_api_key
        if not key or not key.get_secret_value().strip():
            raise LLMError(
                "GEMINI_API_KEY is not configured. Add it to backend/.env to enable the agent.",
                code="missing_api_key",
                recoverable=False,
            )
        return key.get_secret_value()

    def _ensure_client(self) -> genai.Client:
        if self._client is None:
            key = self._require_key()
            self._client = genai.Client(
                api_key=key,
                http_options=types.HttpOptions(
                    api_version=self.settings.gemini_api_version,
                    timeout=int(self.settings.llm_timeout_seconds * 1000),
                ),
            )
        return self._client

    def _config(
        self,
        *,
        tools: list[types.Tool] | None,
        system_instruction: str | None,
    ) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=tools or None,
            temperature=self.settings.llm_temperature,
            max_output_tokens=self.settings.llm_max_output_tokens,
            # The ReAct loop owns tool execution; never let the SDK auto-run it.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    # -------------------------------------------------------------- tools --
    def build_tools(self) -> list[types.Tool]:
        """Expose the backend-registered tools to the model.

        Tool declarations are injected by the :class:`~app.tools.registry.ToolRegistry`
        before the client is called; the client simply returns them.
        """
        return getattr(self, "_tools", []) or []

    def set_tools(self, tools: list[types.Tool]) -> None:
        self._tools = tools

    # ------------------------------------------------------------- turns --
    async def stream_turn(
        self,
        contents: Sequence[types.Content],
        *,
        tools: list[types.Tool],
        system_instruction: str,
    ) -> AsyncIterator[ModelTurn]:
        """Stream one assistant turn, yielding text deltas and tool calls."""
        client = self._ensure_client()
        config = self._config(tools=tools, system_instruction=system_instruction)
        attempt = 0
        collected_parts: list[Any] = []
        while True:
            attempt += 1
            try:
                stream = await client.aio.models.generate_content_stream(
                    model=self.model,
                    contents=list(contents),
                    config=config,
                )
                async for chunk in stream:
                    candidates = getattr(chunk, "candidates", None) or []
                    if not candidates:
                        continue
                    candidate = candidates[0]
                    text = getattr(chunk, "text", None) or ""
                    function_calls = _extract_function_calls(candidate)
                    grounding = getattr(candidate, "grounding_metadata", None)
                    finish = ""
                    finish_enum = getattr(candidate, "finish_reason", None)
                    if finish_enum is not None:
                        finish = getattr(finish_enum, "value", None) or str(finish_enum)

                    _merge_parts(collected_parts, _extract_parts(candidate))

                    if not text and not function_calls and grounding is None:
                        continue
                    yield ModelTurn(
                        text=text,
                        function_calls=function_calls,
                        finish_reason=finish,
                        grounding_metadata=grounding,
                        parts=list(collected_parts),
                    )
                return
            except asyncio.CancelledError:
                raise
            except LLMError as exc:
                if exc.recoverable and attempt < _MAX_ATTEMPTS:
                    await asyncio.sleep(_RETRY_BASE_DELAY * attempt)
                    continue
                raise
            except Exception as exc:  # pragma: no cover - depends on transport
                error = _translate_error(exc)
                if error.recoverable and attempt < _MAX_ATTEMPTS:
                    logger.warning("Gemini request failed (%s); retrying.", error.code)
                    await asyncio.sleep(_RETRY_BASE_DELAY * attempt)
                    continue
                logger.error("Gemini request failed: %s", error.message)
                raise error from exc

    async def generate(
        self,
        contents: Sequence[types.Content] | str,
        *,
        tools: list[types.Tool] | None = None,
        system_instruction: str | None = None,
    ) -> ModelTurn:
        """Execute a single completion (used by the search grounding provider)."""
        client = self._ensure_client()
        config = self._config(tools=tools, system_instruction=system_instruction)
        attempt = 0
        while True:
            attempt += 1
            try:
                response = await client.aio.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                break
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - depends on transport
                error = _translate_error(exc)
                if error.recoverable and attempt < _MAX_ATTEMPTS:
                    logger.warning("Gemini request failed (%s); retrying.", error.code)
                    await asyncio.sleep(_RETRY_BASE_DELAY * attempt)
                    continue
                logger.error("Gemini request failed: %s", error.message)
                raise error from exc

        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            raise LLMError("Gemini returned no candidates.", code="empty_response")
        candidate = candidates[0]
        finish_enum = getattr(candidate, "finish_reason", None)
        finish = getattr(finish_enum, "value", None) or str(finish_enum or "")
        return ModelTurn(
            text=getattr(response, "text", None) or "",
            function_calls=_extract_function_calls(candidate),
            finish_reason=finish,
            grounding_metadata=getattr(candidate, "grounding_metadata", None),
            parts=list(getattr(getattr(candidate, "content", None), "parts", None) or []),
        )

    # ------------------------------------------------------------ status ---
    async def list_models(self) -> list[str]:
        """List the Gemini models reachable with the configured credentials."""
        client = self._ensure_client()
        try:
            pager = await client.aio.models.list()
        except Exception as exc:  # pragma: no cover - network dependent
            raise _translate_error(exc) from exc
        names: list[str] = []
        async for model in pager:
            name = getattr(model, "name", "") or ""
            if name.startswith("models/"):
                name = name[len("models/") :]
            names.append(name)
        return sorted(names)

    async def ping(self) -> tuple[bool, str]:
        """Cheap round-trip used by ``/api/status``."""
        if not self.is_configured:
            return False, "GEMINI_API_KEY is not configured"
        try:
            await self.generate("ping", system_instruction="Reply with the single word: pong")
        except LLMError as exc:
            return False, exc.message
        except Exception as exc:  # pragma: no cover - network dependent
            return False, str(exc)
        return True, f"{self.model} reachable"


def _merge_parts(collected: list[Any], incoming: list[Any]) -> None:
    """Accumulate model parts, keeping the latest version of each tool call.

    A streamed tool call can arrive across several chunks; the last one carries
    the complete arguments and the ``thought_signature`` the API requires when
    the call is replayed on the next turn.
    """
    for part in incoming:
        function_call = getattr(part, "function_call", None)
        if function_call is None and not getattr(part, "thought_signature", None):
            continue
        call_id = getattr(function_call, "id", None) if function_call is not None else None
        if call_id:
            for index, existing in enumerate(collected):
                existing_call = getattr(existing, "function_call", None)
                if existing_call is not None and getattr(existing_call, "id", None) == call_id:
                    collected[index] = part
                    break
            else:
                collected.append(part)
        else:
            collected.append(part)


def _translate_error(exc: Exception) -> LLMError:
    """Map SDK/transport errors onto :class:`LLMError`.

    Classification is driven by the message content rather than by the SDK
    exception class, so it keeps working across ``google-genai`` releases.
    """
    name = type(exc).__name__
    message = str(exc)
    lowered = message.lower()

    if "api key" in lowered or "api_key" in lowered or "permission denied" in lowered:
        return LLMError("Gemini rejected the API key.", code="invalid_api_key", recoverable=False)

    if "quota" in lowered or "resource_exhausted" in lowered:
        # A daily free-tier limit will not clear by retrying - fail fast and
        # tell the user exactly what to change.
        daily = "per day" in lowered or "perday" in lowered or "day limit" in lowered
        return LLMError(
            (
                "The Gemini daily quota for this model is exhausted. Switch "
                "GEMINI_MODEL in backend/.env to another model (for example "
                "gemini-2.5-flash) or wait for the quota to reset."
                if daily
                else "The Gemini rate limit was reached. Try again shortly."
            ),
            code="quota_exceeded",
            recoverable=not daily,
        )

    if "unavailable" in lowered or "503" in message or "overloaded" in lowered:
        return LLMError(
            "The Gemini API is temporarily unavailable (high demand). Retrying…",
            code="service_unavailable",
        )

    if "not found" in lowered or "404" in message:
        return LLMError(
            f"Model '{message[:120]}' is not available for this key.",
            code="model_not_found",
            recoverable=False,
        )

    if "timeout" in lowered or "timed out" in lowered:
        return LLMError("The Gemini request timed out.", code="timeout")

    if "connect" in lowered or "connection" in name.lower():
        return LLMError("Could not reach the Gemini API.", code="network_error")

    if name in {"ClientError", "ServerError", "APIError"}:
        return LLMError(message[:400] or "Gemini request failed.", code="gemini_error")

    return LLMError(message[:400] or name, code="llm_error")


def dumps(payload: Any) -> str:
    """Stable JSON helper used when embedding tool observations."""
    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(payload)
