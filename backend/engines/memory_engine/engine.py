"""
JARVIS OS — Memory Engine (Phase 3)
Persistent memory system: conversations, facts, preferences, and semantic recall.

Three memory layers:
  1. Conversation Memory — rolling chat history persisted to SQLite
  2. Semantic Memory     — facts, preferences, patterns (keyword + FTS search)
  3. Preference Memory   — key-value user preferences

No external vector DB required — uses SQLite FTS5 for full-text search
and TF-IDF-style keyword matching for memory recall.
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func, desc, or_, text
from loguru import logger

from ...config import settings
from ...data.database import AsyncSessionLocal
from ...data.models import Conversation, Memory, Preference
from ...event_bus import event_bus, Event, EventType


# ── Memory Engine ─────────────────────────────────────────────────────────────

class MemoryEngine:
    """
    Manages persistent memory for JARVIS.
    - Stores and retrieves conversation turns
    - Stores semantic memories (facts, preferences, patterns)
    - Provides keyword-based memory search for context injection
    """

    def __init__(self):
        self._session_id: str = str(uuid.uuid4())
        self._ready = False
        # In-memory cache of recent conversations for fast access
        self._conversation_cache: list[dict] = []
        self._max_cache_size = 50

    # ── Conversation Memory ─────────────────────────────────────────────────

    async def store_conversation(
        self,
        role: str,
        content: str,
        intent: Optional[str] = None,
        context_snap: Optional[dict] = None,
    ) -> str:
        """
        Store a single conversation turn (user or jarvis) in the database.
        Returns the conversation ID.
        """
        conv_id = str(uuid.uuid4())
        async with AsyncSessionLocal() as session:
            conv = Conversation(
                id=conv_id,
                session_id=self._session_id,
                role=role,
                content=content,
                intent=intent,
                context_snap=context_snap,
            )
            session.add(conv)
            await session.commit()

        # Update in-memory cache
        entry = {
            "role": role,
            "content": content,
            "intent": intent,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._conversation_cache.append(entry)
        if len(self._conversation_cache) > self._max_cache_size:
            self._conversation_cache = self._conversation_cache[-self._max_cache_size:]

        logger.debug(f"[Memory] Stored conversation: {role} | {content[:60]}...")
        return conv_id

    async def get_recent_conversations(
        self,
        limit: int = 20,
        session_only: bool = False,
    ) -> list[dict]:
        """
        Retrieve recent conversation turns.
        If session_only=True, only returns turns from the current session.
        """
        async with AsyncSessionLocal() as session:
            query = select(Conversation).order_by(desc(Conversation.created_at)).limit(limit)
            if session_only:
                query = query.where(Conversation.session_id == self._session_id)
            result = await session.execute(query)
            rows = result.scalars().all()

        # Return in chronological order (oldest first)
        return [
            {
                "role": row.role,
                "content": row.content,
                "intent": row.intent,
                "timestamp": row.created_at.isoformat() if row.created_at else None,
                "session_id": row.session_id,
            }
            for row in reversed(rows)
        ]

    async def get_conversation_count(self) -> int:
        """Return total number of stored conversation turns."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(func.count(Conversation.id)))
            return result.scalar() or 0

    # ── Semantic Memory (Facts / Knowledge) 

    async def store_memory(
        self,
        content: str,
        memory_type: str = "fact",
        summary: Optional[str] = None,
        tags: Optional[list[str]] = None,
        importance: float = 0.5,
        expires_in_days: Optional[int] = None,
    ) -> str:
        """
        Store a semantic memory — a fact, preference, pattern, or workflow.
        memory_type: fact | preference | workflow | pattern
        """
        mem_id = str(uuid.uuid4())
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        async with AsyncSessionLocal() as session:
            mem = Memory(
                id=mem_id,
                memory_type=memory_type,
                content=content,
                summary=summary or content[:200],
                tags=tags or [],
                importance=importance,
                expires_at=expires_at,
            )
            session.add(mem)
            await session.commit()

        # Publish event
        await event_bus.publish(Event(
            type=EventType.MEMORY_STORED,
            data={"memory_id": mem_id, "type": memory_type, "summary": content[:100]},
            source="memory_engine",
            priority="LOW",
        ))

        logger.info(f"[Memory] Stored {memory_type}: {content[:80]}...")
        return mem_id

    async def search_memories(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 5,
    ) -> list[dict]:
        """
        Search memories by keyword matching against content, summary, and tags.
        Returns the most relevant memories sorted by importance and recency.
        """
        keywords = [w.lower() for w in query.split() if len(w) > 2]
        if not keywords:
            return []

        async with AsyncSessionLocal() as session:
            # Build a query that searches content and summary
            base_query = select(Memory).where(
                Memory.expires_at.is_(None) | (Memory.expires_at > datetime.utcnow())
            )

            if memory_type:
                base_query = base_query.where(Memory.memory_type == memory_type)

            # Keyword matching: OR across all keywords in content + summary
            keyword_filters = []
            for kw in keywords:
                keyword_filters.append(Memory.content.ilike(f"%{kw}%"))
                keyword_filters.append(Memory.summary.ilike(f"%{kw}%"))

            base_query = base_query.where(or_(*keyword_filters))

            # Query up to 50 candidate matches to rank in Python
            result = await session.execute(base_query.limit(50))
            candidate_rows = result.scalars().all()

            # Rank candidates in Python by relevance score
            scored_candidates = []
            for row in candidate_rows:
                score = 0.0
                content_lower = row.content.lower()
                summary_lower = (row.summary or "").lower()
                
                # Check tags safely
                tags = row.tags or []
                if isinstance(tags, str):
                    try:
                        tags = json.loads(tags)
                    except Exception:
                        tags = [tags]
                tags_lower = [str(t).lower() for t in tags]

                for kw in keywords:
                    # Match in content (base weight 1.0 + count weight 0.2)
                    if kw in content_lower:
                        score += 1.0 + (content_lower.count(kw) * 0.2)
                    
                    # Match in summary (base weight 0.5)
                    if kw in summary_lower:
                        score += 0.5 + (summary_lower.count(kw) * 0.1)
                        
                    # Match in tags (high priority: 1.5)
                    if any(kw in tag for tag in tags_lower):
                        score += 1.5

                # Adjust score by database-level importance metrics
                score *= (1.0 + (row.importance or 0.5))
                
                # Slight bump for frequently accessed memories
                score += (row.access_count or 0) * 0.05
                
                scored_candidates.append((score, row))

            # Sort by descending score
            scored_candidates.sort(key=lambda x: x[0], reverse=True)
            
            # Select top rows up to requested limit
            rows = [item[1] for item in scored_candidates[:limit]]

            # Bump access count for retrieved memories
            for row in rows:
                row.access_count = (row.access_count or 0) + 1
            await session.commit()

        return [
            {
                "id": row.id,
                "type": row.memory_type,
                "content": row.content,
                "summary": row.summary,
                "tags": row.tags,
                "importance": row.importance,
                "access_count": row.access_count,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    async def get_all_memories(
        self,
        memory_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Retrieve all memories, optionally filtered by type."""
        async with AsyncSessionLocal() as session:
            query = select(Memory).order_by(desc(Memory.importance), desc(Memory.updated_at)).limit(limit)
            if memory_type:
                query = query.where(Memory.memory_type == memory_type)
            result = await session.execute(query)
            rows = result.scalars().all()

        return [
            {
                "id": row.id,
                "type": row.memory_type,
                "content": row.content,
                "summary": row.summary,
                "tags": row.tags,
                "importance": row.importance,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]

    # ── Preference Memory ────────────────────────────────────────────────────

    async def set_preference(self, key: str, value) -> None:
        """Store or update a user preference."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Preference).where(Preference.key == key)
            )
            pref = result.scalar_one_or_none()

            if pref:
                pref.value = value
                pref.updated_at = datetime.utcnow()
            else:
                pref = Preference(
                    id=str(uuid.uuid4()),
                    key=key,
                    value=value,
                )
                session.add(pref)
            await session.commit()

        logger.debug(f"[Memory] Preference set: {key} = {value}")

    async def get_preference(self, key: str, default=None):
        """Retrieve a user preference by key."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Preference).where(Preference.key == key)
            )
            pref = result.scalar_one_or_none()
            return pref.value if pref else default

    async def get_all_preferences(self) -> dict:
        """Retrieve all user preferences as a dict."""
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Preference))
            rows = result.scalars().all()
        return {row.key: row.value for row in rows}

    # ── Context Builder (for Brain injection) ────────────────────────────────

    async def build_memory_context(self, user_input: str) -> dict:
        """
        Build a memory context block for the Brain Engine.
        Includes: recent conversation history + relevant memories + preferences.
        Cross-session: pulls from ALL past conversations, not just current session.
        """
        # 1. Recent conversations from current session (for immediate context)
        current_session = await self.get_recent_conversations(limit=6, session_only=True)

        # 2. If current session is thin, also pull from previous sessions
        cross_session = []
        if len(current_session) < 4:
            cross_session = await self.get_recent_conversations(limit=10, session_only=False)

        # Merge: current session turns + recent cross-session turns (deduplicated)
        seen_contents = {t["content"] for t in current_session}
        for turn in cross_session:
            if turn["content"] not in seen_contents:
                current_session.append(turn)
                seen_contents.add(turn["content"])

        # 3. Search for relevant memories based on user input
        relevant_memories = await self.search_memories(user_input, limit=5)

        # 4. Get user preferences
        prefs = await self.get_all_preferences()

        # 5. Conversation stats
        total_conversations = await self.get_conversation_count()

        return {
            "recent_conversations": current_session[-20:],  # cap at 20
            "relevant_memories": relevant_memories,
            "preferences": prefs,
            "session_id": self._session_id,
            "total_conversations": total_conversations,
        }

    # ── Event Handlers ───────────────────────────────────────────────────────

    async def _handle_response_generated(self, event: Event) -> None:
        """Auto-store conversation turns when Brain generates a response."""
        text = event.data.get("text", "")
        action = event.data.get("action", "NONE")
        if text:
            await self.store_conversation(
                role="jarvis",
                content=text,
                intent=action,
            )

    async def _handle_text_input(self, event: Event) -> None:
        """Auto-store user input as conversation turn."""
        text = event.data.get("text", "")
        if text:
            await self.store_conversation(
                role="user",
                content=text,
                context_snap=event.data.get("context"),
            )

    # ── Lifecycle ────────────────────────────────────────────────────────────

    async def start(self) -> None:
        """Register event listeners and initialize."""
        event_bus.subscribe(EventType.RESPONSE_GENERATED, self._handle_response_generated)
        event_bus.subscribe(EventType.TEXT_INPUT, self._handle_text_input)
        self._ready = True
        logger.success(f"[Memory] Started — session={self._session_id[:8]}")

    async def stop(self) -> None:
        """Unsubscribe and cleanup."""
        event_bus.unsubscribe(EventType.RESPONSE_GENERATED, self._handle_response_generated)
        event_bus.unsubscribe(EventType.TEXT_INPUT, self._handle_text_input)

        # Log session stats
        count = await self.get_conversation_count()
        logger.info(f"[Memory] Stopped — {count} total conversations stored")

    def new_session(self) -> str:
        """Start a new conversation session. Returns the new session ID."""
        self._session_id = str(uuid.uuid4())
        self._conversation_cache.clear()
        logger.info(f"[Memory] New session: {self._session_id[:8]}")
        return self._session_id


# ── Singleton ──────────────────────────────────────────────────────────────────

memory_engine = MemoryEngine()
