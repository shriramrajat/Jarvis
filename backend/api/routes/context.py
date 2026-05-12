"""
JARVIS OS — Context Routes
Returns the current context snapshot for the frontend dashboard.
"""
from fastapi import APIRouter
from ...engines.context_engine import context_engine

router = APIRouter()


@router.get("/current")
async def get_context():
    """Current session context snapshot."""
    return context_engine.context.to_dict()
