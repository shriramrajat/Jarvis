"""
JARVIS OS — FastAPI Application
REST + WebSocket server. This is the HTTP/WS interface for the Electron frontend.
"""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .config import settings
from .data import init_db
from .event_bus import event_bus
from .runtime.runtime_engine import RuntimeEngine
from .engines.brain_engine import brain_engine
from .engines.memory_engine import memory_engine
from .engines.observation_engine import observation_engine
from .engines.personality_engine import personality_engine
from .engines.automation_engine import automation_engine
from .engines.voice_engine import voice_engine
from .api import router as api_router


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Boot sequence on startup, teardown on shutdown."""
    logger.info(f"[App] {settings.APP_NAME} v{settings.APP_VERSION} booting...")

    # 1. Database
    await init_db()

    # 2. Event Bus
    await event_bus.start()

    # 3. Context Engine — passive monitoring
    await context_engine.start()

    # 4. Brain Engine — AI reasoning
    await brain_engine.start()

    # 5. Memory Engine — persistent conversations & knowledge (Phase 3)
    await memory_engine.start()

    # 6. Observation Engine — proactive monitoring (Phase 3)
    await observation_engine.start()

    # 7. Personality Engine — dynamic prompt modifiers (Phase 3)
    await personality_engine.start()

    # 8. Automation Engine — desktop control
    await automation_engine.start()

    # 9. Voice Engine — wake word + STT + TTS
    await voice_engine.start()

    # 10. WS → Event Bus bridge
    ws_manager.register_listeners()

    logger.success("[App] All services online — ready to serve")

    yield  # ← Server runs here

    # Teardown — reverse order
    logger.info("[App] Shutting down...")
    await voice_engine.stop()
    await automation_engine.stop()
    await memory_engine.stop()
    await personality_engine.stop()
    await observation_engine.stop()
    await brain_engine.stop()
    await context_engine.stop()
    await event_bus.stop()
    logger.info("[App] Shutdown complete")


# ── App Instance ───────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="JARVIS OS — Ambient AI Desktop Assistant Backend",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # Electron localhost doesn't have a fixed port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount REST routes
app.include_router(api_router, prefix="/api/v1")


# ── WebSocket Endpoint ─────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = str(uuid.uuid4())
    await ws_manager.handle_client(websocket, client_id)


# ── Root ───────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "state": state_manager.state.value,
        "mode": state_manager.mode.value,
        "ws_clients": ws_manager.client_count,
    }
