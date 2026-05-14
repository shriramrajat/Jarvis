from fastapi import APIRouter
from .routes.command import router as command_router
from .routes.system import router as system_router
from .routes.memory import router as memory_router

router = APIRouter()
router.include_router(command_router, prefix="/command", tags=["Command"])
router.include_router(system_router, prefix="/system", tags=["System"])
router.include_router(memory_router, prefix="/memory", tags=["Memory"])

__all__ = ["router"]
