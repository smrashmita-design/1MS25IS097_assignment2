"""Conversation persistence.

The store is intentionally decoupled from the agent and the API layer so the
JSON-file implementation can be swapped for PostgreSQL (or any other backend)
without touching a single caller.
"""

from __future__ import annotations

import abc
import asyncio
import functools
import json
import logging
import os
import tempfile
from pathlib import Path

from app.config import Settings, get_settings
from app.schemas.conversation import (
    Conversation,
    ConversationSummary,
    Message,
    SavedSearch,
    SavedSearchCreate,
)

logger = logging.getLogger(__name__)


class ConversationStore(abc.ABC):
    """Interface for conversation and saved-search persistence."""

    @abc.abstractmethod
    async def list_conversations(self) -> list[ConversationSummary]: ...

    @abc.abstractmethod
    async def get_conversation(self, conversation_id: str) -> Conversation | None: ...

    @abc.abstractmethod
    async def create_conversation(self, title: str | None = None) -> Conversation: ...

    @abc.abstractmethod
    async def save_conversation(self, conversation: Conversation) -> Conversation: ...

    @abc.abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool: ...

    @abc.abstractmethod
    async def clear_messages(self, conversation_id: str) -> Conversation | None: ...

    @abc.abstractmethod
    async def list_saved_searches(self) -> list[SavedSearch]: ...

    @abc.abstractmethod
    async def add_saved_search(self, payload: SavedSearchCreate) -> SavedSearch: ...

    @abc.abstractmethod
    async def delete_saved_search(self, search_id: str) -> bool: ...


def _summarise(conversation: Conversation) -> ConversationSummary:
    """Build the sidebar projection for a conversation."""
    preview = ""
    # Prefer the user's own question: it describes the conversation better
    # than the (much longer) assistant answer.
    for message in conversation.messages:
        if message.role == "user" and message.content:
            preview = message.content[:120]
            break
    if not preview:
        for message in reversed(conversation.messages):
            if message.content:
                preview = message.content[:120]
                break
    return ConversationSummary(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=len(conversation.messages),
        preview=preview,
    )


class InMemoryConversationStore(ConversationStore):
    """Volatile store used for tests and when persistence is disabled."""

    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._saved: dict[str, SavedSearch] = {}
        self._lock = asyncio.Lock()

    async def list_conversations(self) -> list[ConversationSummary]:
        async with self._lock:
            items = [_summarise(c) for c in self._conversations.values()]
        items.sort(key=lambda c: c.updated_at, reverse=True)
        return items

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        async with self._lock:
            return self._conversations.get(conversation_id)

    async def create_conversation(self, title: str | None = None) -> Conversation:
        conversation = Conversation(title=title or "New research")
        async with self._lock:
            self._conversations[conversation.id] = conversation
        return conversation

    async def save_conversation(self, conversation: Conversation) -> Conversation:
        conversation.updated_at = conversation.updated_at or conversation.created_at
        async with self._lock:
            self._conversations[conversation.id] = conversation
        return conversation

    async def delete_conversation(self, conversation_id: str) -> bool:
        async with self._lock:
            return self._conversations.pop(conversation_id, None) is not None

    async def clear_messages(self, conversation_id: str) -> Conversation | None:
        async with self._lock:
            conversation = self._conversations.get(conversation_id)
            if conversation is None:
                return None
            conversation.messages = []
            return conversation

    async def list_saved_searches(self) -> list[SavedSearch]:
        async with self._lock:
            items = list(self._saved.values())
        items.sort(key=lambda s: s.created_at, reverse=True)
        return items

    async def add_saved_search(self, payload: SavedSearchCreate) -> SavedSearch:
        search = SavedSearch(**payload.model_dump())
        async with self._lock:
            self._saved[search.id] = search
        return search

    async def delete_saved_search(self, search_id: str) -> bool:
        async with self._lock:
            return self._saved.pop(search_id, None) is not None


class FileConversationStore(InMemoryConversationStore):
    """Durable store backed by a single JSON document on disk.

    Writes are atomic (temp file + replace) and guarded by an asyncio lock so
    concurrent runs cannot corrupt the file.
    """

    def __init__(self, path: Path) -> None:
        super().__init__()
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    # --------------------------------------------------------------- io --
    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read the conversation store (%s); starting empty.", exc)
            return
        for item in raw.get("conversations", []):
            try:
                conversation = Conversation.model_validate(item)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping malformed conversation: %s", exc)
                continue
            self._conversations[conversation.id] = conversation
        for item in raw.get("saved_searches", []):
            try:
                search = SavedSearch.model_validate(item)
            except Exception:  # noqa: BLE001
                continue
            self._saved[search.id] = search

    def _dump(self) -> dict:
        return {
            "conversations": [c.model_dump(mode="json") for c in self._conversations.values()],
            "saved_searches": [s.model_dump(mode="json") for s in self._saved.values()],
        }

    def _flush(self) -> None:
        payload = json.dumps(self._dump(), indent=2, ensure_ascii=False)
        directory = self._path.parent
        handle, temp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as file:
                file.write(payload)
            os.replace(temp_path, self._path)
        except Exception:
            Path(temp_path).unlink(missing_ok=True)
            raise

    def _persist(self) -> None:
        try:
            self._flush()
        except OSError as exc:  # pragma: no cover - filesystem dependent
            logger.warning("Could not persist the conversation store: %s", exc)

    # -------------------------------------------------------- overrides --
    async def create_conversation(self, title: str | None = None) -> Conversation:
        conversation = await super().create_conversation(title)
        self._persist()
        return conversation

    async def save_conversation(self, conversation: Conversation) -> Conversation:
        result = await super().save_conversation(conversation)
        self._persist()
        return result

    async def delete_conversation(self, conversation_id: str) -> bool:
        deleted = await super().delete_conversation(conversation_id)
        if deleted:
            self._persist()
        return deleted

    async def clear_messages(self, conversation_id: str) -> Conversation | None:
        result = await super().clear_messages(conversation_id)
        if result is not None:
            self._persist()
        return result

    async def add_saved_search(self, payload: SavedSearchCreate) -> SavedSearch:
        search = await super().add_saved_search(payload)
        self._persist()
        return search

    async def delete_saved_search(self, search_id: str) -> bool:
        deleted = await super().delete_saved_search(search_id)
        if deleted:
            self._persist()
        return deleted


def build_conversation_store(settings: Settings | None = None) -> ConversationStore:
    """Return the store implementation matching the current configuration.

    The instance is memoised per storage location so that every consumer in
    the process (API routes, the agent controller) operates on the same data.
    """
    settings = settings or get_settings()
    if not settings.persistence_enabled:
        return _shared_memory_store()
    return _shared_file_store(settings.store_dir / "conversations.json")


@functools.lru_cache(maxsize=1)
def _shared_memory_store() -> InMemoryConversationStore:
    return InMemoryConversationStore()


@functools.lru_cache(maxsize=8)
def _shared_file_store(path: Path) -> FileConversationStore:
    return FileConversationStore(path)


def reset_store_cache() -> None:
    """Drop the memoised store instances (used by the test-suite)."""
    _shared_memory_store.cache_clear()
    _shared_file_store.cache_clear()
