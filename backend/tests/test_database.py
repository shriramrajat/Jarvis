import pytest
import uuid
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.data.models import (
    Conversation, Memory, Preference, AutomationLog,
    ObservationSnapshot, SystemEventLog
)

@pytest.mark.asyncio
async def test_conversation_model(db_session: AsyncSession):
    conv_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    
    # Create
    new_conv = Conversation(
        id=conv_id,
        session_id=session_id,
        role="user",
        content="Hello, JARVIS",
        intent="GREETING"
    )
    db_session.add(new_conv)
    await db_session.flush()
    
    # Read
    q = await db_session.execute(select(Conversation).where(Conversation.id == conv_id))
    retrieved = q.scalar_one()
    assert retrieved.content == "Hello, JARVIS"
    assert retrieved.role == "user"
    assert retrieved.intent == "GREETING"

@pytest.mark.asyncio
async def test_memory_model(db_session: AsyncSession):
    mem_id = str(uuid.uuid4())
    
    # Create
    new_mem = Memory(
        id=mem_id,
        memory_type="fact",
        content="User prefers coffee over tea",
        summary="Prefers coffee",
        tags=["preference", "food"],
        importance=0.8
    )
    db_session.add(new_mem)
    await db_session.flush()
    
    # Read
    q = await db_session.execute(select(Memory).where(Memory.id == mem_id))
    retrieved = q.scalar_one()
    assert retrieved.content == "User prefers coffee over tea"
    assert retrieved.importance == 0.8
    assert "food" in retrieved.tags

@pytest.mark.asyncio
async def test_preference_model(db_session: AsyncSession):
    pref_id = str(uuid.uuid4())
    
    # Create
    new_pref = Preference(
        id=pref_id,
        key="theme",
        value={"mode": "dark", "color": "cyan"}
    )
    db_session.add(new_pref)
    await db_session.flush()
    
    # Read
    q = await db_session.execute(select(Preference).where(Preference.id == pref_id))
    retrieved = q.scalar_one()
    assert retrieved.key == "theme"
    assert retrieved.value["mode"] == "dark"

@pytest.mark.asyncio
async def test_automation_log_model(db_session: AsyncSession):
    log_id = str(uuid.uuid4())
    
    # Create
    new_log = AutomationLog(
        id=log_id,
        action_type="open_app",
        command="chrome.exe",
        params={"args": []},
        status="success",
        risk_level="LOW",
        duration_ms=150
    )
    db_session.add(new_log)
    await db_session.flush()
    
    # Read
    q = await db_session.execute(select(AutomationLog).where(AutomationLog.id == log_id))
    retrieved = q.scalar_one()
    assert retrieved.action_type == "open_app"
    assert retrieved.status == "success"

@pytest.mark.asyncio
async def test_observation_snapshot_model(db_session: AsyncSession):
    snap_id = str(uuid.uuid4())
    
    # Create
    new_snap = ObservationSnapshot(
        id=snap_id,
        active_app="vscode",
        window_title="conftest.py - Jarvis",
        cpu_percent=12.5,
        memory_percent=45.2,
        raw_data={"test": "data"}
    )
    db_session.add(new_snap)
    await db_session.flush()
    
    # Read
    q = await db_session.execute(select(ObservationSnapshot).where(ObservationSnapshot.id == snap_id))
    retrieved = q.scalar_one()
    assert retrieved.active_app == "vscode"
    assert retrieved.cpu_percent == 12.5

@pytest.mark.asyncio
async def test_system_event_log_model(db_session: AsyncSession):
    event_id = str(uuid.uuid4())
    
    # Create
    new_event = SystemEventLog(
        id=event_id,
        event_type="system.boot",
        source="kernel",
        data={"time_taken_ms": 1200},
        priority="HIGH"
    )
    db_session.add(new_event)
    await db_session.flush()
    
    # Read
    q = await db_session.execute(select(SystemEventLog).where(SystemEventLog.id == event_id))
    retrieved = q.scalar_one()
    assert retrieved.event_type == "system.boot"
    assert retrieved.priority == "HIGH"
