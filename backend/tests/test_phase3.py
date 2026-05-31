import pytest
import uuid
import os
import shutil
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.data.database import AsyncSessionLocal
from backend.data.models import AutomationLog, ObservationSnapshot, Memory
from backend.event_bus import event_bus, Event, EventType
from backend.state import state_manager, JarvisState, JarvisMode
from backend.engines.automation_engine.engine import automation_engine
from backend.engines.observation_engine.engine import observation_engine


@pytest.mark.asyncio
async def test_automation_log_recording(db_session: AsyncSession):
    # Mock event execution
    cmd_id = str(uuid.uuid4())
    event = Event(
        type=EventType.EXECUTION_STARTED,
        data={
            "command_id": cmd_id,
            "action": "SET_MODE",
            "params": {"mode": "NORMAL"},
            "risk": "LOW"
        },
        source="test"
    )
    
    # Run the handler directly to test logging side effect
    await automation_engine._handle_execution(event)
    
    # Verify DB entry
    await asyncio.sleep(0.1)  # allow commit to propagate
    q = await db_session.execute(
        select(AutomationLog).where(AutomationLog.action_type == "SET_MODE")
    )
    log = q.scalars().all()
    assert len(log) > 0
    assert log[-1].status == "success"
    assert log[-1].risk_level == "LOW"
    assert log[-1].duration_ms >= 0
    assert log[-1].command == "set mode: NORMAL"


@pytest.mark.asyncio
async def test_observation_snapshot_deduplication(db_session: AsyncSession):
    # Setup initial state
    observation_engine._last_saved_snapshot_time = None
    observation_engine._last_saved_app = None
    observation_engine._last_saved_title = None

    # Clear previous snapshots
    async with AsyncSessionLocal() as session:
        await session.execute(ObservationSnapshot.__table__.delete())
        await session.commit()

    # 1. First update - should save
    event1 = Event(
        type=EventType.CONTEXT_UPDATED,
        data={
            "active_app": "vscode",
            "active_window_title": "App.jsx - Jarvis",
            "cpu_percent": 10.0,
            "memory_percent": 40.0
        }
    )
    await observation_engine._handle_context_updated(event1)
    
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(ObservationSnapshot))
        snaps = res.scalars().all()
        assert len(snaps) == 1
        assert snaps[0].active_app == "vscode"

    # 2. Same update - should not save (deduplication)
    await observation_engine._handle_context_updated(event1)
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(ObservationSnapshot))
        snaps = res.scalars().all()
        assert len(snaps) == 1  # count unchanged

    # 3. App change - should save
    event2 = Event(
        type=EventType.CONTEXT_UPDATED,
        data={
            "active_app": "chrome",
            "active_window_title": "Google Search",
            "cpu_percent": 12.0,
            "memory_percent": 42.0
        }
    )
    await observation_engine._handle_context_updated(event2)
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(ObservationSnapshot))
        snaps = res.scalars().all()
        assert len(snaps) == 2
        assert snaps[-1].active_app == "chrome"


@pytest.mark.asyncio
async def test_pattern_recognition_learning(db_session: AsyncSession):
    # Setup mock snapshots history
    # Clear previous snapshots
    async with AsyncSessionLocal() as session:
        await session.execute(ObservationSnapshot.__table__.delete())
        await session.execute(Memory.__table__.delete())
        await session.commit()

    now = datetime.utcnow()
    # Create transition history: chrome -> spotify 4 times
    snaps_to_add = []
    for i in range(4):
        # A transition occurs within 1 minute
        t1 = now - timedelta(hours=24 * (4 - i))
        t2 = t1 + timedelta(seconds=60)
        
        snaps_to_add.append(ObservationSnapshot(
            id=str(uuid.uuid4()),
            active_app="chrome",
            window_title="Search",
            created_at=t1
        ))
        snaps_to_add.append(ObservationSnapshot(
            id=str(uuid.uuid4()),
            active_app="spotify",
            window_title="Music",
            created_at=t2
        ))

    # Create time-of-day history: vscode at 9 AM on 4 distinct days
    for i in range(4):
        t = now - timedelta(days=i+1)
        t = t.replace(hour=9, minute=15, second=0)
        snaps_to_add.append(ObservationSnapshot(
            id=str(uuid.uuid4()),
            active_app="vscode",
            window_title="Editor",
            created_at=t
        ))

    async with AsyncSessionLocal() as session:
        session.add_all(snaps_to_add)
        await session.commit()

    # Trigger learning
    await observation_engine.learn_habits_and_patterns()

    # Verify patterns saved as memories
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Memory).where(Memory.memory_type == "pattern"))
        patterns = res.scalars().all()
        
        assert len(patterns) >= 2
        contents = [p.content for p in patterns]
        assert any("spotify" in c and "chrome" in c for c in contents)
        assert any("vscode" in c and "09:00" in c for c in contents)


@pytest.mark.asyncio
async def test_proactive_suggestion_trigger():
    # Setup patterns manually in observation_engine cache
    observation_engine._patterns = {
        "transitions": {
            "chrome": ["spotify"]
        },
        "time_of_day": {}
    }
    observation_engine._last_alert_time = None
    observation_engine._last_saved_app = "vscode" # simulates a change from vscode to chrome
    
    # Set mock state to IDLE
    state_manager._state = JarvisState.IDLE
    
    # Setup event listener for suggestion
    suggestion_event = None
    async def suggestion_handler(event: Event):
        nonlocal suggestion_event
        suggestion_event = event

    event_bus.subscribe(EventType.PROACTIVE_SUGGESTION, suggestion_handler)

    # Start event bus
    await event_bus.start()
    try:
        # Trigger context update representing transition to Chrome
        event = Event(
            type=EventType.CONTEXT_UPDATED,
            data={
                "active_app": "chrome",
                "active_window_title": "Google Search",
                "cpu_percent": 5.0,
                "memory_percent": 30.0
            }
        )
        
        # We also need to mock snapshot DB checking since the engine searches if suggest_app was active recently
        # Let's verify that a proactive alert event is fired
        await observation_engine._handle_context_updated(event)
        
        # Wait for event bus to process the queue
        await asyncio.sleep(0.1)
        
        assert suggestion_event is not None
        assert "spotify" in suggestion_event.data["message"]
        assert "chrome" in suggestion_event.data["message"]
    finally:
        event_bus.unsubscribe(EventType.PROACTIVE_SUGGESTION, suggestion_handler)
        await event_bus.stop()


@pytest.mark.asyncio
async def test_file_operations():
    test_dir = Path("backend/tests/scratch_file_ops").resolve()
    test_dir.mkdir(parents=True, exist_ok=True)
    file_path = test_dir / "test_file.txt"
    dest_path = test_dir / "moved_file.txt"

    try:
        # 1. Create/Write
        create_res = await automation_engine._file_operation({
            "op": "create",
            "path": str(file_path),
            "content": "Hello, JARVIS"
        })
        assert create_res["status"] == "success"
        assert file_path.exists()

        # 2. Read
        read_res = await automation_engine._file_operation({
            "op": "read",
            "path": str(file_path)
        })
        assert read_res["content"] == "Hello, JARVIS"

        # 3. Append
        append_res = await automation_engine._file_operation({
            "op": "append",
            "path": str(file_path),
            "content": "\nNew Line"
        })
        assert append_res["status"] == "success"
        
        read_res2 = await automation_engine._file_operation({
            "op": "read",
            "path": str(file_path)
        })
        assert read_res2["content"] == "Hello, JARVIS\nNew Line"

        # 4. List
        list_res = await automation_engine._file_operation({
            "op": "list",
            "path": str(test_dir)
        })
        assert len(list_res["items"]) >= 1
        assert any(item["name"] == "test_file.txt" for item in list_res["items"])

        # 5. Move
        move_res = await automation_engine._file_operation({
            "op": "move",
            "path": str(file_path),
            "destination": str(dest_path)
        })
        assert move_res["status"] == "success"
        assert not file_path.exists()
        assert dest_path.exists()

        # 6. Delete
        delete_res = await automation_engine._file_operation({
            "op": "delete",
            "path": str(dest_path)
        })
        assert delete_res["status"] == "success"
        assert not dest_path.exists()

    finally:
        if test_dir.exists():
            shutil.rmtree(test_dir)
