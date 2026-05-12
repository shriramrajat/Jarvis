"""
JARVIS OS — Runtime Engine
The central orchestrator. Boots all engines, manages lifecycle, handles shutdown.
This is the first thing that starts and the last thing that stops.
"""
import asyncio
import signal
import sys
from loguru import logger

from ..config import settings
from ..event_bus import event_bus, Event, EventType
from ..state import state_manager, JarvisState
from ..engines.context_engine import context_engine


class RuntimeEngine:
    """
    Boots JARVIS OS:
    1. Configure logging
    2. Start Event Bus
    3. Initialize all engines
    4. Transition to IDLE
    5. Wait for shutdown signal
    """

    def __init__(self):
        self._shutdown_event = asyncio.Event()
        self._engines: list = []

    def _configure_logging(self) -> None:
        logger.remove()
        logger.add(
            sys.stderr,
            level=settings.LOG_LEVEL,
            format=(
                "<green>{time:HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan> — "
                "<level>{message}</level>"
            ),
            colorize=True,
        )
        logger.add(
            settings.LOG_PATH,
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            compression="zip",
        )
        logger.success(f"[Runtime] Logging configured → {settings.LOG_PATH}")

    async def _boot_engines(self) -> None:
        """Start all engines in correct order."""
        logger.info("[Runtime] Booting engines...")

        # 1. Event Bus — must be first
        await event_bus.start()

        # 2. Context Engine — passive monitoring
        await context_engine.start()

        logger.success("[Runtime] All engines booted")

    async def _shutdown_engines(self) -> None:
        """Graceful shutdown in reverse order."""
        logger.info("[Runtime] Shutting down engines...")
        await context_engine.stop()
        await event_bus.stop()
        logger.info("[Runtime] All engines stopped")

    async def _handle_shutdown(self, _event: Event) -> None:
        logger.info("[Runtime] Shutdown event received")
        self._shutdown_event.set()

    async def run(self) -> None:
        """Main entry point. Call this to start JARVIS OS."""
        self._configure_logging()

        logger.info(f"[Runtime] Starting {settings.APP_NAME} v{settings.APP_VERSION}")

        # Subscribe to shutdown events
        event_bus.subscribe(EventType.SYSTEM_SHUTDOWN, self._handle_shutdown)

        await self._boot_engines()

        # Announce boot
        await event_bus.publish(Event(
            type=EventType.SYSTEM_BOOT,
            data={"version": settings.APP_VERSION},
            source="runtime",
            priority="HIGH",
        ))

        # Transition to IDLE
        await state_manager.transition(JarvisState.IDLE, source="runtime")

        # Signal ready
        await event_bus.publish(Event(
            type=EventType.SYSTEM_READY,
            data={"message": "JARVIS OS is online"},
            source="runtime",
            priority="HIGH",
        ))

        logger.success(f"[Runtime] {settings.APP_NAME} is ONLINE ✓")

        # Wait for shutdown
        await self._shutdown_event.wait()

        # Graceful shutdown
        await state_manager.force_state(JarvisState.SHUTDOWN)
        await self._shutdown_engines()
        logger.info("[Runtime] JARVIS OS shutdown complete")

    async def shutdown(self) -> None:
        """Trigger a graceful shutdown programmatically."""
        await event_bus.publish(Event(
            type=EventType.SYSTEM_SHUTDOWN,
            data={},
            source="runtime",
            priority="HIGH",
        ))
