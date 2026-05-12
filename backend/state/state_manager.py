"""
JARVIS OS — State Manager
Single source of truth for the current system state and mode.
All state transitions happen here, emitting STATE_CHANGED events.
"""
import asyncio
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from loguru import logger

from ..event_bus import event_bus, Event, EventType


# ── State Definitions ─────────────────────────────────────────────────────────

class JarvisState(str, Enum):
    """Operational states of JARVIS — what it is currently doing."""
    IDLE               = "IDLE"
    LISTENING          = "LISTENING"
    THINKING           = "THINKING"
    EXECUTING          = "EXECUTING"
    SPEAKING           = "SPEAKING"
    WAITING_CONFIRM    = "WAITING_CONFIRMATION"
    ERROR              = "ERROR"
    INTERRUPTED        = "INTERRUPTED"
    SHUTDOWN           = "SHUTDOWN"


class JarvisMode(str, Enum):
    """Operating modes — affects behavior across all engines."""
    NORMAL             = "NORMAL"        # Default: responsive, interactive
    OBSERVATION        = "OBSERVATION"   # Passive monitoring, pattern detection
    FOCUS              = "FOCUS"         # Minimal interruptions
    AUTOMATION         = "AUTOMATION"    # Autonomous task execution
    SLEEP              = "SLEEP"         # Minimal processing, wake-word only


# ── Valid Transitions ─────────────────────────────────────────────────────────

VALID_TRANSITIONS: dict[JarvisState, set[JarvisState]] = {
    JarvisState.IDLE:            {JarvisState.LISTENING, JarvisState.THINKING, JarvisState.SHUTDOWN},
    JarvisState.LISTENING:       {JarvisState.THINKING, JarvisState.IDLE, JarvisState.INTERRUPTED},
    JarvisState.THINKING:        {JarvisState.EXECUTING, JarvisState.SPEAKING, JarvisState.WAITING_CONFIRM, JarvisState.ERROR, JarvisState.IDLE},
    JarvisState.EXECUTING:       {JarvisState.SPEAKING, JarvisState.ERROR, JarvisState.IDLE},
    JarvisState.SPEAKING:        {JarvisState.IDLE, JarvisState.LISTENING},
    JarvisState.WAITING_CONFIRM: {JarvisState.EXECUTING, JarvisState.IDLE},
    JarvisState.ERROR:           {JarvisState.IDLE},
    JarvisState.INTERRUPTED:     {JarvisState.IDLE, JarvisState.LISTENING},
    JarvisState.SHUTDOWN:        set(),
}


# ── State Snapshot ─────────────────────────────────────────────────────────────

@dataclass
class StateSnapshot:
    state: JarvisState
    mode: JarvisMode
    previous_state: Optional[JarvisState]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    meta: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "state": self.state.value,
            "mode": self.mode.value,
            "previous_state": self.previous_state.value if self.previous_state else None,
            "timestamp": self.timestamp.isoformat(),
            "meta": self.meta,
        }


# ── State Manager ─────────────────────────────────────────────────────────────

class StateManager:
    def __init__(self):
        self._state = JarvisState.IDLE
        self._mode = JarvisMode.NORMAL
        self._previous_state: Optional[JarvisState] = None
        self._history: list[StateSnapshot] = []
        self._lock = asyncio.Lock()

    @property
    def state(self) -> JarvisState:
        return self._state

    @property
    def mode(self) -> JarvisMode:
        return self._mode

    @property
    def snapshot(self) -> StateSnapshot:
        return StateSnapshot(
            state=self._state,
            mode=self._mode,
            previous_state=self._previous_state,
        )

    async def transition(
        self,
        new_state: JarvisState,
        meta: dict | None = None,
        source: str = "system",
    ) -> bool:
        """
        Attempt a state transition. Returns True if successful.
        Validates against the allowed transition table.
        """
        async with self._lock:
            if new_state not in VALID_TRANSITIONS.get(self._state, set()):
                logger.warning(
                    f"[StateManager] Invalid transition: {self._state} → {new_state} "
                    f"(allowed: {VALID_TRANSITIONS.get(self._state, set())})"
                )
                return False

            previous = self._state
            self._previous_state = previous
            self._state = new_state

            snapshot = StateSnapshot(
                state=new_state,
                mode=self._mode,
                previous_state=previous,
                meta=meta or {},
            )
            self._history.append(snapshot)

            logger.info(f"[StateManager] {previous.value} → {new_state.value} | mode={self._mode.value}")

            await event_bus.publish(Event(
                type=EventType.STATE_CHANGED,
                data=snapshot.to_dict(),
                source=source,
                priority="HIGH",
            ))
            return True

    async def set_mode(self, new_mode: JarvisMode, source: str = "system") -> None:
        """Switch operating mode."""
        async with self._lock:
            previous_mode = self._mode
            self._mode = new_mode
            logger.info(f"[StateManager] Mode: {previous_mode.value} → {new_mode.value}")

            await event_bus.publish(Event(
                type=EventType.MODE_CHANGED,
                data={"previous_mode": previous_mode.value, "mode": new_mode.value},
                source=source,
                priority="MEDIUM",
            ))

    async def force_state(self, state: JarvisState, meta: dict | None = None) -> None:
        """Force a state without transition validation. Use only for error recovery."""
        async with self._lock:
            previous = self._state
            self._previous_state = previous
            self._state = state
            logger.warning(f"[StateManager] FORCE: {previous.value} → {state.value}")

    def get_history(self, limit: int = 50) -> list[dict]:
        return [s.to_dict() for s in self._history[-limit:]]


# ── Singleton ──────────────────────────────────────────────────────────────────

state_manager = StateManager()
