"""Shared FastAPI dependencies."""

from __future__ import annotations

import functools

from app.agent.controller import AgentController
from app.config import Settings, get_settings
from app.services.conversation_store import ConversationStore, build_conversation_store


@functools.lru_cache(maxsize=1)
def get_store() -> ConversationStore:
    """Return the process-wide conversation store."""
    return build_conversation_store()


@functools.lru_cache(maxsize=1)
def get_controller() -> AgentController:
    """Return the process-wide agent controller.

    The controller must share the *same* store instance as the API routes,
    otherwise a conversation created through the API would be invisible to the
    agent (and vice versa).
    """
    return AgentController(store=get_store())


def get_app_settings() -> Settings:
    """Return the process-wide settings."""
    return get_settings()


def reset_dependencies() -> None:
    """Clear cached singletons (used by the test-suite)."""
    from app.services.conversation_store import reset_store_cache

    get_controller.cache_clear()
    get_store.cache_clear()
    reset_store_cache()
