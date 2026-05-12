"""
JARVIS OS — Context Engine
Maintains the current session context: active app, project, tasks, user intent history.
Think of this as JARVIS's working memory for the current session.
"""
import asyncio
import psutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any
from loguru import logger

from ...event_bus import event_bus, Event, EventType


@dataclass
class ActiveContext:
    """Snapshot of the current user environment."""
    active_app: str = "unknown"
    active_window_title: str = ""
    current_project: Optional[str] = None
    current_task: Optional[str] = None
    recent_intents: list[str] = field(default_factory=list)
    session_start: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "active_app": self.active_app,
            "active_window_title": self.active_window_title,
            "current_project": self.current_project,
            "current_task": self.current_task,
            "recent_intents": self.recent_intents[-10:],
            "session_start": self.session_start.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "extra": self.extra,
        }


class ContextEngine:
    """
    Tracks and maintains real-time session context.
    Publishes CONTEXT_UPDATED events whenever context changes significantly.
    """

    def __init__(self, snapshot_interval: int = 10):
        self._context = ActiveContext()
        self._lock = asyncio.Lock()
        self._snapshot_interval = snapshot_interval
        self._monitor_task: asyncio.Task | None = None

    @property
    def context(self) -> ActiveContext:
        return self._context

    async def update(self, **kwargs) -> None:
        """Update specific context fields."""
        async with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._context, key):
                    setattr(self._context, key, value)
            self._context.last_updated = datetime.utcnow()

        await event_bus.publish(Event(
            type=EventType.CONTEXT_UPDATED,
            data=self._context.to_dict(),
            source="context_engine",
            priority="LOW",
        ))

    async def add_intent(self, intent: str) -> None:
        """Record a recognized user intent into history."""
        async with self._lock:
            self._context.recent_intents.append(intent)
            if len(self._context.recent_intents) > 50:
                self._context.recent_intents = self._context.recent_intents[-50:]
            self._context.last_updated = datetime.utcnow()

    async def _system_snapshot(self) -> None:
        """Capture lightweight system metrics."""
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent

            # Get foreground window on Windows
            active_app = "unknown"
            window_title = ""
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                    window_title = buf.value

                # Get process name for the foreground window
                pid = ctypes.c_ulong()
                ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                try:
                    proc = psutil.Process(pid.value)
                    active_app = proc.name().replace(".exe", "")
                except Exception:
                    pass
            except Exception:
                pass

            await self.update(
                cpu_percent=cpu,
                memory_percent=mem,
                active_app=active_app,
                active_window_title=window_title,
            )
        except Exception as e:
            logger.warning(f"[ContextEngine] Snapshot error: {e}")

    async def _monitor_loop(self) -> None:
        """Periodic system context collection."""
        logger.info("[ContextEngine] Monitor loop started")
        while True:
            await self._system_snapshot()
            await asyncio.sleep(self._snapshot_interval)

    async def start(self) -> None:
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.success("[ContextEngine] Started")

    async def stop(self) -> None:
        if self._monitor_task:
            self._monitor_task.cancel()
        logger.info("[ContextEngine] Stopped")


# ── Singleton ──────────────────────────────────────────────────────────────────

context_engine = ContextEngine()
