"""
JARVIS OS — Event Bus
Central pub/sub system. Every engine publishes and subscribes via this bus.
No engine talks to another engine directly — all communication goes through here.
"""
import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Coroutine
from loguru import logger


# ── Event Types ────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    # System lifecycle
    SYSTEM_BOOT          = "system.boot"
    SYSTEM_READY         = "system.ready"
    SYSTEM_SHUTDOWN      = "system.shutdown"
    SYSTEM_ERROR         = "system.error"

    # State changes
    STATE_CHANGED        = "state.changed"
    MODE_CHANGED         = "mode.changed"

    # Input events
    WAKE_WORD_DETECTED   = "input.wake_word"
    VOICE_INPUT          = "input.voice"
    TEXT_INPUT           = "input.text"
    HOTKEY_TRIGGERED     = "input.hotkey"
    GUI_INPUT            = "input.gui"

    # Processing events
    INTENT_RECOGNIZED    = "processing.intent"
    CONTEXT_UPDATED      = "processing.context"
    TASK_PLANNED         = "processing.task_planned"
    PERMISSION_REQUIRED  = "processing.permission_required"
    PERMISSION_GRANTED   = "processing.permission_granted"
    PERMISSION_DENIED    = "processing.permission_denied"

    # Execution events
    EXECUTION_STARTED    = "execution.started"
    EXECUTION_COMPLETED  = "execution.completed"
    EXECUTION_FAILED     = "execution.failed"

    # Response events
    RESPONSE_GENERATED   = "response.generated"
    TTS_SPEAK            = "response.tts_speak"
    GUI_NOTIFICATION     = "response.gui_notification"

    # Memory events
    MEMORY_STORED        = "memory.stored"
    MEMORY_RETRIEVED     = "memory.retrieved"

    # Observation events
    OBSERVATION_SNAPSHOT = "observation.snapshot"
    PATTERN_DETECTED     = "observation.pattern"
    PROACTIVE_SUGGESTION = "observation.suggestion"

    # Voice engine events
    LISTENING_STARTED    = "voice.listening_started"
    LISTENING_STOPPED    = "voice.listening_stopped"

    # Automation events
    APP_OPENED           = "automation.app_opened"
    APP_CLOSED           = "automation.app_closed"
    COMMAND_EXECUTED     = "automation.command_executed"


# ── Event Payload ──────────────────────────────────────────────────────────────

@dataclass
class Event:
    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: str = "MEDIUM"  # HIGH | MEDIUM | LOW

    def __repr__(self) -> str:
        return f"Event(type={self.type}, source={self.source}, id={self.event_id[:8]})"


# ── Event Bus ─────────────────────────────────────────────────────────────────

HandlerType = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Async pub/sub event bus.
    - Subscribers register handlers per event type.
    - Publishers fire events that are dispatched to all subscribers.
    - Priority queue: HIGH events are dispatched before MEDIUM/LOW.
    """

    def __init__(self):
        self._subscribers: dict[EventType, list[HandlerType]] = defaultdict(list)
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running = False
        self._worker_task: asyncio.Task | None = None
        self._priority_map = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        self._counter = 0   # tiebreaker so Events are never compared directly

    def subscribe(self, event_type: EventType, handler: HandlerType) -> None:
        """Register a handler for an event type."""
        self._subscribers[event_type].append(handler)
        logger.debug(f"[EventBus] Subscribed {handler.__qualname__} → {event_type}")

    def unsubscribe(self, event_type: EventType, handler: HandlerType) -> None:
        """Remove a handler."""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(self, event: Event) -> None:
        """Enqueue an event for dispatching."""
        priority = self._priority_map.get(event.priority, 1)
        self._counter += 1
        await self._queue.put((priority, self._counter, event))
        logger.debug(f"[EventBus] Published → {event}")

    async def publish_sync(self, event: Event) -> None:
        """Dispatch an event immediately (bypass queue). Use for high-priority sync needs."""
        await self._dispatch(event)

    async def _dispatch(self, event: Event) -> None:
        handlers = self._subscribers.get(event.type, [])
        if not handlers:
            logger.debug(f"[EventBus] No handlers for {event.type}")
            return
        tasks = [handler(event) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result, handler in zip(results, handlers):
            if isinstance(result, Exception):
                logger.error(f"[EventBus] Handler {handler.__qualname__} raised: {result}")

    async def _worker(self) -> None:
        """Background worker that drains the event queue."""
        logger.info("[EventBus] Worker started")
        while self._running:
            try:
                _, _seq, event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                try:
                    await self._dispatch(event)
                finally:
                    self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"[EventBus] Worker error: {e}")

    async def start(self) -> None:
        self._running = True
        self._worker_task = asyncio.create_task(self._worker())
        logger.success("[EventBus] Started")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            await self._queue.join()
            self._worker_task.cancel()
        logger.info("[EventBus] Stopped")


# ── Singleton ──────────────────────────────────────────────────────────────────

event_bus = EventBus()
