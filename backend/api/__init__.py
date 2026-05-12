"""
JARVIS OS — API Router (v1)
Aggregates all REST endpoint sub-routers.
"""
from fastapi import APIRouter
from .routes import system, command, memory, context

router = APIRouter()

router.include_router(system.router,  prefix="/system",  tags=["System"])
router.include_router(command.router, prefix="/command", tags=["Commands"])
router.include_router(memory.router,  prefix="/memory",  tags=["Memory"])
router.include_router(context.router, prefix="/context", tags=["Context"])
