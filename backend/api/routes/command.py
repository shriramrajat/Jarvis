"""
JARVIS OS — Command Routes
Text input endpoint: accepts a user command and routes it into the Event Bus.
Phase 2 will hook the brain/NLU here. For now it echoes with state transitions.
"""
import uuid
from fastapi import APIRouter
from pydantic import BaseModel

from ...event_bus import event_bus, Event, EventType
from ...state import state_manager, JarvisState

router = APIRouter()


class CommandRequest(BaseModel):
    text: str
    source: str = "text"    # text | gui | voice


class CommandResponse(BaseModel):
    command_id: str
    received: str
    status: str


@router.post("/send", response_model=CommandResponse)
async def send_command(req: CommandRequest):
    """
    Accept a user command. Transition to THINKING and fire TEXT_INPUT event.
    The brain (Phase 2) will subscribe to TEXT_INPUT and process it.
    """
    command_id = str(uuid.uuid4())

    # Transition state
    await state_manager.transition(JarvisState.THINKING, source="command_api")

    # Publish the input event
    await event_bus.publish(Event(
        type=EventType.TEXT_INPUT,
        data={
            "command_id": command_id,
            "text": req.text,
            "source": req.source,
        },
        source="api",
        priority="HIGH",
    ))

    return CommandResponse(
        command_id=command_id,
        received=req.text,
        status="processing",
    )
