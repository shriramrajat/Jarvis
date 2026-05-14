"""
JARVIS OS — Chronos Engine (Phase 4)
Handles time-based events, cron jobs, and scheduled reminders.
Uses APScheduler to execute tasks asynchronously.
"""
from datetime import datetime, timedelta
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ...event_bus import event_bus, Event, EventType


class ChronosEngine:
    """
    Schedules background tasks and proactive reminders.
    """
    def __init__(self):
        self._scheduler = AsyncIOScheduler()
        self._ready = False

    async def _handle_reminder_trigger(self, message: str) -> None:
        """Called when a scheduled reminder fires. Triggers the Brain/Voice."""
        logger.info(f"[Chronos] Triggering reminder: {message}")
        
        # Publish PROACTIVE_SUGGESTION to make JARVIS speak it automatically
        await event_bus.publish(Event(
            type=EventType.PROACTIVE_SUGGESTION,
            data={"message": message},
            source="chronos",
            priority="HIGH",
        ))

        # Also publish response generated so the frontend sees it and TTS speaks it
        await event_bus.publish(Event(
            type=EventType.RESPONSE_GENERATED,
            data={
                "command_id": f"reminder_{int(datetime.utcnow().timestamp())}",
                "text": message,
                "action": "NONE",
                "risk": "LOW",
                "requires_confirmation": False,
            },
            source="chronos",
            priority="HIGH",
        ))

    def schedule_reminder(self, message: str, delay_seconds: int) -> None:
        """Schedule a one-off reminder."""
        run_date = datetime.now() + timedelta(seconds=delay_seconds)
        self._scheduler.add_job(
            self._handle_reminder_trigger,
            'date',
            run_date=run_date,
            args=[message],
            id=f"rem_{int(run_date.timestamp())}",
            replace_existing=True
        )
        logger.info(f"[Chronos] Scheduled reminder for {delay_seconds}s from now: '{message}'")

    async def _hourly_check(self) -> None:
        """Example background cron task: simple hourly tick."""
        logger.debug("[Chronos] Hourly background check running")

    async def start(self) -> None:
        """Start the scheduler and register default cron jobs."""
        if self._ready:
            return
            
        # Register an hourly background task
        self._scheduler.add_job(
            self._hourly_check,
            'interval',
            hours=1,
            id='hourly_sys_check',
            replace_existing=True
        )

        self._scheduler.start()
        self._ready = True
        logger.success("[Chronos] Started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if self._ready:
            self._scheduler.shutdown(wait=False)
            self._ready = False
            logger.info("[Chronos] Stopped")


# ── Singleton ──
chronos_engine = ChronosEngine()
