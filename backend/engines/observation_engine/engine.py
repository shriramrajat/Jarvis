"""
JARVIS OS — Observation Engine (Phase 3)
Passively monitors system context to detect anomalies and trigger proactive suggestions.
"""
import asyncio
from datetime import datetime, timedelta
from loguru import logger

from ...event_bus import event_bus, Event, EventType
from ...state import state_manager, JarvisState


class ObservationEngine:
    """
    Monitors system context for patterns and anomalies.
    If an anomaly is detected, it triggers a proactive suggestion.
    """
    def __init__(self):
        self._ready = False
        
        # State tracking for anomalies
        self._high_cpu_start: datetime | None = None
        self._high_cpu_threshold = 90.0
        self._high_cpu_duration_sec = 60 * 5  # 5 minutes

        self._high_mem_start: datetime | None = None
        self._high_mem_threshold = 90.0
        self._high_mem_duration_sec = 60 * 5

        # Debounce proactive alerts so JARVIS doesn't spam
        self._last_alert_time: datetime | None = None
        self._alert_cooldown_sec = 60 * 15  # 15 minutes between proactive alerts

    async def _handle_context_updated(self, event: Event) -> None:
        """Analyze new context for anomalies."""
        # Only interrupt if JARVIS is IDLE
        if state_manager.state.value != JarvisState.IDLE.value:
            return

        # Check cooldown
        now = datetime.utcnow()
        if self._last_alert_time and (now - self._last_alert_time).total_seconds() < self._alert_cooldown_sec:
            return

        ctx = event.data
        cpu = ctx.get("cpu_percent", 0.0)
        mem = ctx.get("memory_percent", 0.0)

        # ── CPU Anomaly Detection ──
        if cpu >= self._high_cpu_threshold:
            if not self._high_cpu_start:
                self._high_cpu_start = now
            elif (now - self._high_cpu_start).total_seconds() > self._high_cpu_duration_sec:
                await self._trigger_proactive_alert(
                    f"Sir, system CPU usage has been critically high at {cpu:.1f}% for over 5 minutes. Would you like me to identify the resource-intensive processes?"
                )
                self._high_cpu_start = None  # Reset after alert
        else:
            self._high_cpu_start = None

        # ── Memory Anomaly Detection ──
        if mem >= self._high_mem_threshold:
            if not self._high_mem_start:
                self._high_mem_start = now
            elif (now - self._high_mem_start).total_seconds() > self._high_mem_duration_sec:
                await self._trigger_proactive_alert(
                    f"Sir, system memory is running low. Utilization has exceeded {mem:.1f}% for over 5 minutes. Should I attempt to clear the standby list?"
                )
                self._high_mem_start = None
        else:
            self._high_mem_start = None


    async def _trigger_proactive_alert(self, message: str) -> None:
        """Trigger JARVIS to speak a proactive alert."""
        logger.warning(f"[Observation] Triggering proactive alert: {message}")
        self._last_alert_time = datetime.utcnow()
        
        # Publish PROACTIVE_SUGGESTION event
        await event_bus.publish(Event(
            type=EventType.PROACTIVE_SUGGESTION,
            data={"message": message},
            source="observation_engine",
            priority="HIGH",
        ))

        # Directly trigger response generation so JARVIS speaks
        await event_bus.publish(Event(
            type=EventType.RESPONSE_GENERATED,
            data={
                "command_id": "proactive_alert",
                "text": message,
                "action": "NONE",
                "risk": "LOW",
                "requires_confirmation": False,
            },
            source="observation_engine",
            priority="HIGH",
        ))
        
        # Transition state to speaking
        await state_manager.transition(JarvisState.SPEAKING, source="observation_engine")

    async def start(self) -> None:
        event_bus.subscribe(EventType.CONTEXT_UPDATED, self._handle_context_updated)
        self._ready = True
        logger.success("[Observation] Started")

    async def stop(self) -> None:
        event_bus.unsubscribe(EventType.CONTEXT_UPDATED, self._handle_context_updated)
        logger.info("[Observation] Stopped")

# ── Singleton ──
observation_engine = ObservationEngine()
