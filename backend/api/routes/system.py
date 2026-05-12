"""
JARVIS OS — System Routes
Health, status, state management, mode switching.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...state import state_manager, JarvisState, JarvisMode
from ...event_bus import event_bus, Event, EventType
from ...config import settings

router = APIRouter()


class StateTransitionRequest(BaseModel):
    state: JarvisState
    meta: dict = {}


class ModeChangeRequest(BaseModel):
    mode: JarvisMode


@router.get("/health")
async def health():
    """System health check — used by Electron to verify backend is running."""
    return {
        "status": "healthy",
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "state": state_manager.state.value,
        "mode": state_manager.mode.value,
    }


@router.get("/status")
async def status():
    """Full system status snapshot."""
    return state_manager.snapshot.to_dict()


@router.post("/state")
async def transition_state(req: StateTransitionRequest):
    """Manually trigger a state transition (testing + GUI controls)."""
    success = await state_manager.transition(req.state, meta=req.meta, source="api")
    if not success:
        raise HTTPException(
            status_code=409,
            detail=f"Invalid transition: {state_manager.state} → {req.state}",
        )
    return {"success": True, "state": req.state.value}


@router.post("/mode")
async def change_mode(req: ModeChangeRequest):
    """Switch operating mode."""
    await state_manager.set_mode(req.mode, source="api")
    return {"success": True, "mode": req.mode.value}


@router.get("/history")
async def state_history(limit: int = 20):
    """Recent state transition history."""
    return {"history": state_manager.get_history(limit)}


@router.post("/shutdown")
async def shutdown():
    """Trigger graceful shutdown."""
    await event_bus.publish(Event(
        type=EventType.SYSTEM_SHUTDOWN,
        data={"source": "api"},
        source="api",
        priority="HIGH",
    ))
    return {"message": "Shutdown initiated"}
