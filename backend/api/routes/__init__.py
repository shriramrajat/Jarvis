from fastapi import APIRouter
from .command import router as command_router
from .system import router as system_router
from .memory import router as memory_router

# The context router was deleted, so we won't import it here right now, 
# but if it's required we can recreate it. For now, just command, system, memory.
