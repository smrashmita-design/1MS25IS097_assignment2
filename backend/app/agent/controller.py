"""The agent controller.

Coordinates a single research run: loads conversation context, executes the
ReAct loop, streams lifecycle events and persists the finished turn.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Any

from google.genai import types

from app.agent.events import EventFactory
from app.agent.loop import ReActLoop, RunOutcome
from app.config import Settings, get_settings
from app.llm.client import LLMClient
from app.llm.gemini_client import GeminiClient
from app.schemas.conversation import Conversation, Message, SavedSearchCreate, Source
from app.schemas.events import AgentEvent, AgentEventType
from app.search.base import SearchProvider
from app.search.factory import build_search_provider
from app.services.conversation_store import ConversationStore, build_conversation_store
from app.tools.registry import ToolRegistry
from app.tools.search_tool import build_search_tool

logger = logging.getLogger(__name__)


class AgentController:
    """Application service that owns one agent runtime."""

    def __init__(
        self,
        settings: Settings | None = None,
        llm: LLMClient | None = None,
        search_provider: SearchProvider | None = None,
        registry: ToolRegistry | None = None,
        store: ConversationStore | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.llm: LLMClient = llm or GeminiClient(self.settings)
        self.search_provider: SearchProvider = search_provider or build_search_provider(
            self.settings, self.llm
        )
        self.registry: ToolRegistry = registry or self._build_registry()
        self.store: ConversationStore = store or build_conversation_store(self.settings)
        self.loop = ReActLoop(self.llm, self.registry, self.settings)
        self._runs: dict[str, bool] = {}

    # ------------------------------------------------------------- setup --
    def _build_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        spec, validator = build_search_tool(self.search_provider, self.settings)
        registry.register(spec, validator)
        return registry

    @property
    def model(self) -> str:
        return getattr(self.llm, "model", self.settings.gemini_model)

    @property
    def provider_name(self) -> str:
        return self.search_provider.name

    # ------------------------------------------------------- run control --
    def request_stop(self, run_id: str) -> bool:
        """Flag a run for cancellation. Returns ``True`` if the run was known."""
        if run_id in self._runs:
            self._runs[run_id] = True
            return True
        return False

    # -------------------------------------------------------------- runs --
    async def stream_run(
        self,
        *,
        message: str,
        conversation_id: str | None = None,
        run_id: str | None = None,
        max_iterations: int | None = None,
        save_search: bool = False,
    ) -> AsyncIterator[AgentEvent]:
        """Execute a full research turn and yield timeline events."""
        run_id = run_id or uuid.uuid4().hex
        self._runs[run_id] = False

        factory = EventFactory()
        started = time.perf_counter()
        outcome = RunOutcome()

        # ---------------------------------------------------------- setup --
        conversation = await self._ensure_conversation(conversation_id)
        conversation.messages.append(Message(role="user", content=message))

        if not self.settings.gemini_configured:
            yield factory.build(
                AgentEventType.AGENT_ERROR,
                title="Gemini is not configured",
                detail=(
                    "GEMINI_API_KEY is missing on the backend. Copy backend/.env.example "
                    "to backend/.env and add your key."
                ),
                data={"code": "missing_api_key", "run_id": run_id},
            )
            await self.store.save_conversation(conversation)
            self._runs.pop(run_id, None)
            return

        yield factory.build(
            AgentEventType.AGENT_STARTED,
            title="Query received",
            detail=message[:280],
            data={
                "run_id": run_id,
                "conversation_id": conversation.id,
                "query": message,
                "model": self.model,
                "search_provider": self.provider_name,
                "tools": self.registry.names(),
            },
        )

        if save_search:
            await self.store.add_saved_search(
                SavedSearchCreate(query=message[:500], conversation_id=conversation.id)
            )

        contents = self._build_contents(conversation, message)
        collected_sources: dict[str, Source] = {}
        assistant_events: list[dict[str, Any]] = []
        final_text = ""
        error: str | None = None
        cancelled = False

        def _capture_observation(_result, payload: dict[str, Any]) -> None:
            for item in payload.get("results") or []:
                url = item.get("url")
                if not url or url in collected_sources:
                    continue
                collected_sources[url] = Source(
                    title=item.get("title") or url,
                    url=url,
                    snippet=item.get("snippet") or "",
                    source=item.get("source") or item.get("domain") or "",
                    domain=item.get("domain") or "",
                    rank=int(item.get("position") or len(collected_sources) + 1),
                )

        try:
            async for event in self.loop.run(
                contents,
                factory=factory,
                outcome=outcome,
                max_iterations=max_iterations,
                should_stop=lambda: self._runs.get(run_id, False),
                on_observation=_capture_observation,
            ):
                assistant_events.append(event.model_dump(mode="json"))
                if event.type is AgentEventType.FINAL_ANSWER:
                    final_text = str(event.data.get("content") or "")
                elif event.type is AgentEventType.AGENT_ERROR:
                    error = str(event.detail or "The agent run failed.")
                elif event.type is AgentEventType.AGENT_CANCELLED:
                    cancelled = True
                yield event
        finally:
            self._runs.pop(run_id, None)

        duration_ms = int((time.perf_counter() - started) * 1000)
        sources = sorted(collected_sources.values(), key=lambda s: s.rank)

        assistant_message = Message(
            role="assistant",
            content=final_text,
            sources=sources,
            events=assistant_events,
            iterations=outcome.iterations,
            tool_calls=outcome.tool_calls,
            duration_ms=duration_ms,
            status="error" if error else ("cancelled" if cancelled else "complete"),
            error=error,
            model=self.model,
            provider=self.provider_name,
        )
        conversation.messages.append(assistant_message)
        conversation.updated_at = datetime.now(timezone.utc)
        if len(conversation.messages) == 2 and conversation.title in ("", "New research"):
            conversation.title = _derive_title(message)
        await self.store.save_conversation(conversation)

        if error:
            yield factory.build(
                AgentEventType.AGENT_ERROR,
                title="Run failed",
                detail=error,
                data={"code": "agent_error", "duration_ms": duration_ms},
            )
            return

        yield factory.build(
            AgentEventType.AGENT_COMPLETED,
            title="Completed",
            detail=(
                f"Answered in {outcome.iterations} iteration(s) using "
                f"{outcome.tool_calls} tool call(s)."
            ),
            data={
                "run_id": run_id,
                "conversation_id": conversation.id,
                "iterations": outcome.iterations,
                "tool_calls": outcome.tool_calls,
                "duration_ms": duration_ms,
                "source_count": len(sources),
                "sources": [source.model_dump(mode="json") for source in sources],
                "message_id": assistant_message.id,
            },
        )

    # ---------------------------------------------------------- helpers --
    async def _ensure_conversation(self, conversation_id: str | None) -> Conversation:
        if conversation_id:
            existing = await self.store.get_conversation(conversation_id)
            if existing is not None:
                return existing
        return await self.store.create_conversation()

    def _build_contents(self, conversation: Conversation, message: str) -> list[types.Content]:
        """Build the model context from prior turns plus the new query."""
        contents: list[types.Content] = []
        history = conversation.messages[-max(2, self.settings.max_history_messages) :]
        for item in history:
            if item.role == "user" and item.content:
                contents.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=item.content)])
                )
            elif item.role == "assistant" and item.content:
                context = item.content
                if item.sources:
                    links = ", ".join(f"{s.title} ({s.url})" for s in item.sources[:8])
                    context = f"{context}\n\n[Sources you cited earlier: {links}]"
                contents.append(
                    types.Content(role="model", parts=[types.Part.from_text(text=context)])
                )
        return contents


def _derive_title(message: str) -> str:
    """Build a short conversation title from the first user message."""
    cleaned = " ".join(message.split())
    if len(cleaned) <= 58:
        return cleaned
    truncated = cleaned[:58]
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return truncated + "…"
