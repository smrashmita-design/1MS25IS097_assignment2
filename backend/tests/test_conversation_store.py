"""Tests for the conversation store."""

from __future__ import annotations

from app.schemas.conversation import Message, SavedSearchCreate
from app.services.conversation_store import (
    FileConversationStore,
    InMemoryConversationStore,
)


class TestInMemoryStore:
    async def test_crud_lifecycle(self) -> None:
        store = InMemoryConversationStore()
        conversation = await store.create_conversation("Test")
        assert conversation.title == "Test"

        conversation.messages.append(Message(role="user", content="hello"))
        await store.save_conversation(conversation)

        summaries = await store.list_conversations()
        assert len(summaries) == 1
        assert summaries[0].message_count == 1
        assert summaries[0].preview == "hello"

        loaded = await store.get_conversation(conversation.id)
        assert loaded is not None
        assert loaded.messages[0].content == "hello"

        assert await store.delete_conversation(conversation.id) is True
        assert await store.get_conversation(conversation.id) is None

    async def test_clear_messages(self) -> None:
        store = InMemoryConversationStore()
        conversation = await store.create_conversation()
        conversation.messages.append(Message(role="user", content="x"))
        await store.save_conversation(conversation)

        cleared = await store.clear_messages(conversation.id)
        assert cleared is not None
        assert cleared.messages == []

    async def test_saved_searches(self) -> None:
        store = InMemoryConversationStore()
        search = await store.add_saved_search(SavedSearchCreate(query="ai research"))
        assert search.query == "ai research"
        assert len(await store.list_saved_searches()) == 1
        assert await store.delete_saved_search(search.id) is True
        assert await store.list_saved_searches() == []


class TestFileStore:
    async def test_conversations_survive_a_restart(self, tmp_path) -> None:
        path = tmp_path / "conversations.json"
        store = FileConversationStore(path)
        conversation = await store.create_conversation("Persisted")
        conversation.messages.append(Message(role="user", content="remember me"))
        await store.save_conversation(conversation)
        await store.add_saved_search(SavedSearchCreate(query="saved"))

        assert path.exists()

        reloaded = FileConversationStore(path)
        loaded = await reloaded.get_conversation(conversation.id)
        assert loaded is not None
        assert loaded.title == "Persisted"
        assert loaded.messages[0].content == "remember me"
        assert len(await reloaded.list_saved_searches()) == 1

    async def test_malformed_file_does_not_crash_the_store(self, tmp_path) -> None:
        path = tmp_path / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        store = FileConversationStore(path)
        assert await store.list_conversations() == []
