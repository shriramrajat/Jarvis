"""
JARVIS OS — Backend Entry Point
Run with: uvicorn main:app --host 127.0.0.1 --port 8000 --reload
"""
import uvicorn
from backend.app import app
from backend.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
