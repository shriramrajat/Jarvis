"""
JARVIS OS — Memory Routes
Basic CRUD for memories. Phase 2 will add semantic search.
"""
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...data import get_session, Memory

router = APIRouter()


class MemoryCreate(BaseModel):
    memory_type: str   # fact | preference | workflow | pattern
    content: str
    summary: str | None = None
    tags: list[str] = []
    importance: float = 0.5


@router.get("/")
async def list_memories(
    memory_type: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    q = select(Memory).order_by(Memory.created_at.desc()).limit(limit)
    if memory_type:
        q = q.where(Memory.memory_type == memory_type)
    result = await session.execute(q)
    memories = result.scalars().all()
    return [
        {
            "id": m.id,
            "type": m.memory_type,
            "content": m.content,
            "summary": m.summary,
            "tags": m.tags,
            "importance": m.importance,
            "access_count": m.access_count,
            "created_at": m.created_at.isoformat(),
        }
        for m in memories
    ]


@router.post("/", status_code=201)
async def create_memory(
    req: MemoryCreate,
    session: AsyncSession = Depends(get_session),
):
    memory = Memory(
        id=str(uuid.uuid4()),
        memory_type=req.memory_type,
        content=req.content,
        summary=req.summary,
        tags=req.tags,
        importance=req.importance,
    )
    session.add(memory)
    await session.flush()
    return {"id": memory.id, "status": "created"}


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
