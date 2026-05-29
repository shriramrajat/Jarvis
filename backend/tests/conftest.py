import os
import sys
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

# 1. Override environment variables BEFORE any imports of backend components
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["DB_PATH"] = ":memory:"
os.environ["DEBUG"] = "False"

# 2. Modify settings object directly
from backend.config.settings import settings
settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
settings.DB_PATH = ":memory:"
settings.DEBUG = False

# 3. Mock all hardware and heavy external engines before importing app/database
from backend.engines.voice_engine import voice_engine
from backend.engines.brain_engine import brain_engine
from backend.engines.automation_engine import automation_engine
from backend.engines.observation_engine import observation_engine
from backend.engines.personality_engine import personality_engine
from backend.engines.chronos_engine import chronos_engine
from backend.engines.context_engine import context_engine

# Replace engine startup/lifecycle methods with mocks
voice_engine.start = AsyncMock()
voice_engine.stop = AsyncMock()
brain_engine.start = AsyncMock()
brain_engine.stop = AsyncMock()
automation_engine.start = AsyncMock()
automation_engine.stop = AsyncMock()
observation_engine.start = AsyncMock()
observation_engine.stop = AsyncMock()
personality_engine.start = AsyncMock()
personality_engine.stop = AsyncMock()
chronos_engine.start = AsyncMock()
chronos_engine.stop = AsyncMock()
context_engine.start = AsyncMock()
context_engine.stop = AsyncMock()

# Mock brain engine's external client/API calls
brain_engine._call_ai = AsyncMock(return_value={
    "response": "Hello from mock JARVIS.",
    "action": "NONE",
    "params": {},
    "risk": "LOW",
    "requires_confirmation": False
})

# Mock voice engine sound device loops
voice_engine._load_tts_engine = MagicMock()
voice_engine._load_wake_word_model = MagicMock()
voice_engine._load_whisper_model = MagicMock()

# Now we can safely import app and db components
from backend.data.database import engine, Base, AsyncSessionLocal
from backend.app import app
from httpx import AsyncClient, ASGITransport

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    """Initialise test database schema in memory."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session():
    """Provide a clean async DB session per test, rolling back after use."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def client():
    """Provide an HTTPX async test client for the FastAPI app."""
    # Use ASGITransport for newer httpx versions
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture(autouse=True)
async def reset_singletons():
    """Reset the global event_bus queue/subscribers and state_manager state for each test."""
    from backend.event_bus import event_bus
    from backend.state.state_manager import state_manager, JarvisState, JarvisMode
    
    # 1. Direct state reset to avoid queuing event bus messages during setup
    state_manager._state = JarvisState.IDLE
    state_manager._mode = JarvisMode.NORMAL
    state_manager._previous_state = None
    state_manager._history.clear()
    
    # 2. Stop the event_bus if it is running
    event_bus._running = False
    if event_bus._worker_task:
        event_bus._worker_task.cancel()
        event_bus._worker_task = None

    # 3. Clear event_bus queue
    while not event_bus._queue.empty():
        try:
            event_bus._queue.get_nowait()
            event_bus._queue.task_done()
        except asyncio.QueueEmpty:
            break
    
    yield


