"""Conversation and saved-search management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_store
from app.schemas.conversation import (
    Conversation,
    ConversationCreate,
    ConversationSummary,
    RenameConversationRequest,
    SavedSearch,
    SavedSearchCreate,
)
from app.services.conversation_store import ConversationStore

router = APIRouter(tags=["conversations"])


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(store: ConversationStore = Depends(get_store)) -> list[ConversationSummary]:
    """List conversations ordered by most recently updated."""
    return await store.list_conversations()


@router.post("/conversations", response_model=Conversation, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate | None = None,
    store: ConversationStore = Depends(get_store),
) -> Conversation:
    """Create an empty conversation."""
    title = payload.title if payload else None
    return await store.create_conversation(title)


@router.get("/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str, store: ConversationStore = Depends(get_store)
) -> Conversation:
    """Return a conversation with its full message history and timelines."""
    conversation = await store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@router.patch("/conversations/{conversation_id}", response_model=Conversation)
async def rename_conversation(
    conversation_id: str,
    payload: RenameConversationRequest,
    store: ConversationStore = Depends(get_store),
) -> Conversation:
    """Rename a conversation."""
    conversation = await store.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    conversation.title = payload.title.strip() or conversation.title
    return await store.save_conversation(conversation)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str, store: ConversationStore = Depends(get_store)
) -> dict[str, bool]:
    """Delete a conversation permanently."""
    deleted = await store.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return {"deleted": True}


@router.delete("/conversations/{conversation_id}/messages", response_model=Conversation)
async def clear_conversation(
    conversation_id: str, store: ConversationStore = Depends(get_store)
) -> Conversation:
    """Remove every message from a conversation without deleting it."""
    conversation = await store.clear_messages(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@router.get("/saved-searches", response_model=list[SavedSearch])
async def list_saved_searches(store: ConversationStore = Depends(get_store)) -> list[SavedSearch]:
    """List saved searches."""
    return await store.list_saved_searches()


@router.post("/saved-searches", response_model=SavedSearch, status_code=status.HTTP_201_CREATED)
async def add_saved_search(
    payload: SavedSearchCreate, store: ConversationStore = Depends(get_store)
) -> SavedSearch:
    """Persist a search for later reuse."""
    return await store.add_saved_search(payload)


@router.delete("/saved-searches/{search_id}")
async def delete_saved_search(
    search_id: str, store: ConversationStore = Depends(get_store)
) -> dict[str, bool]:
    """Remove a saved search."""
    deleted = await store.delete_saved_search(search_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Saved search not found.")
    return {"deleted": True}
