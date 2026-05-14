"""
JARVIS OS — Memory Routes
CRUD for memories + semantic search + conversation history.
Phase 3: Full persistent memory system.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...data import get_session, Memory
from ...engines.memory_engine import memory_engine

router = APIRouter()


class MemoryCreate(BaseModel):
    memory_type: str   # fact | preference | workflow | pattern
    content: str
    summary: str | None = None
    tags: list[str] = []
    importance: float = 0.5


class PreferenceSet(BaseModel):
    key: str
    value: str | int | float | bool | list | dict


# ── Memory CRUD ──────────────────────────────────────────────────────────────

@router.get("/")
async def list_memories(
    memory_type: str | None = None,
    limit: int = 50,
):
    """List all stored memories, optionally filtered by type."""
    memories = await memory_engine.get_all_memories(memory_type=memory_type, limit=limit)
    return memories


@router.post("/", status_code=201)
async def create_memory(req: MemoryCreate):
    """Manually store a memory."""
    mem_id = await memory_engine.store_memory(
        content=req.content,
        memory_type=req.memory_type,
        summary=req.summary,
        tags=req.tags,
        importance=req.importance,
    )
    return {"id": mem_id, "status": "created"}


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Memory).where(Memory.id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    await session.delete(memory)
    return {"status": "deleted"}


# ── Memory Search ────────────────────────────────────────────────────────────

@router.get("/search")
async def search_memories(
    q: str = Query(..., description="Search query"),
    memory_type: str | None = None,
    limit: int = 5,
):
    """Search memories by keyword matching."""
    results = await memory_engine.search_memories(
        query=q,
        memory_type=memory_type,
        limit=limit,
    )
    return results


# ── Conversation History ─────────────────────────────────────────────────────

@router.get("/conversations")
async def get_conversations(
    limit: int = 30,
    session_only: bool = False,
):
    """Retrieve recent conversation turns."""
    conversations = await memory_engine.get_recent_conversations(
        limit=limit,
        session_only=session_only,
    )
    return {
        "session_id": memory_engine._session_id,
        "total_stored": await memory_engine.get_conversation_count(),
        "conversations": conversations,
    }


@router.post("/conversations/new-session")
async def new_session():
    """Start a new conversation session."""
    session_id = memory_engine.new_session()
    return {"session_id": session_id, "status": "new_session_started"}


# ── Preferences ──────────────────────────────────────────────────────────────

@router.get("/preferences")
async def get_preferences():
    """Get all user preferences."""
    prefs = await memory_engine.get_all_preferences()
    return prefs


@router.post("/preferences")
async def set_preference(req: PreferenceSet):
    """Set or update a user preference."""
    await memory_engine.set_preference(req.key, req.value)
    return {"key": req.key, "status": "saved"}

