"""
JARVIS OS — Observation Engine (Phase 3)
Passively monitors system context to detect anomalies and trigger proactive suggestions.
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from loguru import logger

from ...event_bus import event_bus, Event, EventType
from ...state import state_manager, JarvisState
from ...data.database import AsyncSessionLocal
from ...data.models import ObservationSnapshot, Memory


class ObservationEngine:
    """
    Monitors system context for patterns and anomalies.
    Saves snapshots to DB and performs proactive pattern and habit detection.
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

        # Snapshot DB storage rate limiting
        self._last_saved_snapshot_time: datetime | None = None
        self._last_saved_app: str | None = None
        self._last_saved_title: str | None = None

        # Cache for pattern memories
        self._patterns = {"transitions": {}, "time_of_day": {}}

    async def load_patterns(self) -> None:
        """Load pattern memories from database into cache."""
        self._patterns = {"transitions": {}, "time_of_day": {}}
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(Memory).where(Memory.memory_type == "pattern")
                )
                memories = result.scalars().all()
                
            for mem in memories:
                tags = mem.tags or []
                if isinstance(tags, str):
                    import json
                    try:
                        tags = json.loads(tags)
                    except Exception:
                        tags = []
                
                if "transition" in tags:
                    trigger_app = None
                    suggest_app = None
                    for t in tags:
                        if t.startswith("trigger:"):
                            trigger_app = t.split(":", 1)[1].lower()
                        elif t.startswith("suggest:"):
                            suggest_app = t.split(":", 1)[1].lower()
                    if trigger_app and suggest_app:
                        if trigger_app not in self._patterns["transitions"]:
                            self._patterns["transitions"][trigger_app] = []
                        self._patterns["transitions"][trigger_app].append(suggest_app)
                        
                elif "time" in tags:
                    hour = None
                    suggest_app = None
                    for t in tags:
                        if t.startswith("hour:"):
                            try:
                                hour = int(t.split(":", 1)[1])
                            except ValueError:
                                pass
                        elif t.startswith("suggest:"):
                            suggest_app = t.split(":", 1)[1].lower()
                    if hour is not None and suggest_app:
                        if hour not in self._patterns["time_of_day"]:
                            self._patterns["time_of_day"][hour] = []
                        self._patterns["time_of_day"][hour].append(suggest_app)
                        
            logger.info(f"[Observation] Loaded {len(memories)} pattern memories into cache")
        except Exception as e:
            logger.warning(f"[Observation] Failed to load pattern memories: {e}")

    async def _handle_context_updated(self, event: Event) -> None:
        """Analyze new context for anomalies and save to DB."""
        ctx = event.data
        app = ctx.get("active_app", "unknown")
        title = ctx.get("active_window_title", "")
        cpu = ctx.get("cpu_percent", 0.0)
        mem = ctx.get("memory_percent", 0.0)
        
        now = datetime.utcnow()

        # 1. Save snapshot to DB (with rate-limiting/change detection optimization)
        should_save = (
            self._last_saved_snapshot_time is None or
            app != self._last_saved_app or
            title != self._last_saved_title or
            (now - self._last_saved_snapshot_time).total_seconds() >= 300
        )

        if should_save:
            try:
                async with AsyncSessionLocal() as session:
                    snapshot = ObservationSnapshot(
                        id=str(uuid.uuid4()),
                        active_app=app,
                        window_title=title,
                        cpu_percent=cpu,
                        memory_percent=mem,
                        raw_data=ctx,
                    )
                    session.add(snapshot)
                    await session.commit()
                self._last_saved_snapshot_time = now
                self._last_saved_app = app
                self._last_saved_title = title
            except Exception as e:
                logger.warning(f"[Observation] Failed to save snapshot to database: {e}")

        # 2. Check proactive suggestions / pattern matching
        await self._check_proactive_habits(app, now)

        # 3. Anomaly Detection (only when JARVIS is IDLE)
        if state_manager.state.value != JarvisState.IDLE.value:
            return

        # Check cooldown for anomaly triggers
        if self._last_alert_time and (now - self._last_alert_time).total_seconds() < self._alert_cooldown_sec:
            return

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

    async def _check_proactive_habits(self, current_app: str, now: datetime) -> None:
        """Check if current state matches any learned habits to suggest actions."""
        if state_manager.state.value != JarvisState.IDLE.value:
            return
            
        if self._last_alert_time and (now - self._last_alert_time).total_seconds() < self._alert_cooldown_sec:
            return
            
        current_app_lower = (current_app or "").lower().strip()
        if not current_app_lower or current_app_lower == "unknown":
            return
            
        # 1. Check transition patterns (e.g. Chrome -> Spotify)
        if current_app_lower != (self._last_saved_app or "").lower() and current_app_lower in self._patterns["transitions"]:
            suggestions = self._patterns["transitions"][current_app_lower]
            for suggest_app in suggestions:
                # Check if suggested app was active in last 5 minutes
                is_running = False
                try:
                    async with AsyncSessionLocal() as session:
                        from sqlalchemy import select
                        five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
                        result = await session.execute(
                            select(ObservationSnapshot)
                            .where(ObservationSnapshot.active_app == suggest_app)
                            .where(ObservationSnapshot.created_at >= five_mins_ago)
                            .limit(1)
                        )
                        if result.scalar():
                            is_running = True
                except Exception:
                    pass
                    
                if not is_running:
                    await self._trigger_proactive_alert(
                        f"Sir, I notice you usually open {suggest_app} after launching {current_app}. Would you like me to launch it?"
                    )
                    return
                    
        # 2. Check time-of-day patterns (e.g. VS Code at 9 AM)
        current_hour = now.hour
        if current_hour in self._patterns["time_of_day"]:
            suggestions = self._patterns["time_of_day"][current_hour]
            for suggest_app in suggestions:
                # Check if suggest_app has been active today
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                is_active_today = False
                try:
                    async with AsyncSessionLocal() as session:
                        from sqlalchemy import select
                        result = await session.execute(
                            select(ObservationSnapshot)
                            .where(ObservationSnapshot.active_app == suggest_app)
                            .where(ObservationSnapshot.created_at >= today_start)
                            .limit(1)
                        )
                        if result.scalar():
                            is_active_today = True
                except Exception:
                    pass
                    
                if not is_active_today:
                    await self._trigger_proactive_alert(
                        f"Sir, you usually work on {suggest_app} around this time. Shall I launch it for you?"
                    )
                    return

    async def learn_habits_and_patterns(self) -> None:
        """Analyze historical snapshots to detect user habits and patterns."""
        logger.info("[Observation] Starting habit and pattern learning analysis...")
        
        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(select(ObservationSnapshot).order_by(ObservationSnapshot.created_at))
            snapshots = result.scalars().all()
            
        if len(snapshots) < 10:
            logger.info("[Observation] Not enough historical snapshots to learn patterns yet.")
            return
            
        # ── 1. Analyze Time-of-Day App Habits ──
        from collections import defaultdict
        
        app_hour_days = defaultdict(lambda: defaultdict(set))
        total_days = set()
        
        for snap in snapshots:
            if not snap.active_app or snap.active_app == "unknown":
                continue
            day_str = snap.created_at.strftime("%Y-%m-%d")
            hour = snap.created_at.hour
            app_hour_days[snap.active_app.lower()][hour].add(day_str)
            total_days.add(day_str)
            
        num_total_days = len(total_days)
        new_patterns = []
        
        # Criteria: Active in that hour block on >= 3 distinct days and in >= 50% of distinct days recorded
        for app, hours in app_hour_days.items():
            for hour, days in hours.items():
                num_active_days = len(days)
                if num_active_days >= 3 and (num_active_days / max(1, num_total_days)) >= 0.5:
                    new_patterns.append({
                        "type": "time",
                        "content": f"You usually use {app} between {hour:02d}:00 and {(hour+1)%24:02d}:00.",
                        "tags": ["pattern", "time", f"hour:{hour}", f"suggest:{app}"],
                        "importance": 0.6
                    })
                    
        # ── 2. Analyze App Transition Habits ──
        transitions = defaultdict(int)
        app_occurrences = defaultdict(int)
        
        for i in range(len(snapshots) - 1):
            snap_a = snapshots[i]
            snap_b = snapshots[i+1]
            
            app_a = (snap_a.active_app or "").lower()
            app_b = (snap_b.active_app or "").lower()
            
            if not app_a or app_a == "unknown" or not app_b or app_b == "unknown":
                continue
                
            if app_a == app_b:
                continue
                
            # If within 5 minutes (300 seconds)
            time_diff = (snap_b.created_at - snap_a.created_at).total_seconds()
            if time_diff <= 300:
                transitions[(app_a, app_b)] += 1
                app_occurrences[app_a] += 1
                
        # Criteria: Transition A -> B occurred >= 3 times, and represents >= 60% of A's transitions
        for (app_a, app_b), count in transitions.items():
            total_transitions_from_a = app_occurrences[app_a]
            if count >= 3 and (count / max(1, total_transitions_from_a)) >= 0.6:
                new_patterns.append({
                    "type": "transition",
                    "content": f"You usually open {app_b} after launching {app_a}.",
                    "tags": ["pattern", "transition", f"trigger:{app_a}", f"suggest:{app_b}"],
                    "importance": 0.7
                })
                
        # Write new patterns to database
        try:
            async with AsyncSessionLocal() as session:
                for pat in new_patterns:
                    stmt = select(Memory).where(Memory.memory_type == "pattern").where(Memory.content == pat["content"])
                    res = await session.execute(stmt)
                    existing = res.scalar()
                    if not existing:
                        logger.info(f"[Observation] Learned new pattern memory: {pat['content']}")
                        new_mem = Memory(
                            id=str(uuid.uuid4()),
                            memory_type="pattern",
                            content=pat["content"],
                            summary=pat["content"],
                            tags=pat["tags"],
                            importance=pat["importance"],
                        )
                        session.add(new_mem)
                await session.commit()
                
            # Refresh memory cache
            await self.load_patterns()
            
        except Exception as e:
            logger.error(f"[Observation] Failed to save learned patterns: {e}")

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

    async def _initial_learning_delay(self) -> None:
        await asyncio.sleep(5.0)
        try:
            await self.learn_habits_and_patterns()
        except Exception as e:
            logger.warning(f"[Observation] Initial pattern learning failed: {e}")

    async def start(self) -> None:
        await self.load_patterns()
        event_bus.subscribe(EventType.CONTEXT_UPDATED, self._handle_context_updated)
        self._ready = True
        logger.success("[Observation] Started")
        asyncio.create_task(self._initial_learning_delay())

    async def stop(self) -> None:
        event_bus.unsubscribe(EventType.CONTEXT_UPDATED, self._handle_context_updated)
        logger.info("[Observation] Stopped")

# ── Singleton ──
observation_engine = ObservationEngine()

