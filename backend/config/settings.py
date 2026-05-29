"""
JARVIS OS — Central Configuration
All settings pulled from environment or .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR    = Path(__file__).resolve().parent.parent          # = backend/
PROJECT_DIR = BASE_DIR.parent                                   # = Jarvis/  ← .env lives here


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "JARVIS OS"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # ── Server ───────────────────────────────────────────
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # ── Database ─────────────────────────────────────────
    DB_PATH: str = str(BASE_DIR / "data" / "db" / "jarvis.db")
    DATABASE_URL: str = f"sqlite+aiosqlite:///{str(BASE_DIR / 'data' / 'db' / 'jarvis.db')}"

    # ── AI (Google Gemini — OpenAI-compatible) ───────────────────────────────
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    AI_MODEL: str = "gemini-2.0-flash"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 2048

    # ── AI (Local Offline / Ollama) ───────────────────────────────────────────
    OLLAMA_ENABLED: bool = True  # Toggle this to False to fall back to Cloud API
    OLLAMA_HOST: str = "http://127.0.0.1:11434"
    OLLAMA_MODEL: str = "llama3.2:1b"


    # ── Voice ────────────────────────────────────────────────────────────────
    WAKE_WORD: str = "hey_jarvis"     # OpenWakeWord built-in model name
    STT_MODEL: str = "base"           # tiny | base | small | medium | large-v3
    TTS_VOICE: str = "en_US-arctic-medium"

    # Piper TTS Paths
    PIPER_EXE: str = str(BASE_DIR / "bin" / "piper" / "piper.exe")
    PIPER_VOICES_DIR: str = str(BASE_DIR / "bin" / "piper" / "voices")

    # ── Observation ──────────────────────────────────────
    OBSERVATION_MODE: bool = False
    OBSERVATION_INTERVAL: int = 5    # seconds between context snapshots

    # ── Logging ──────────────────────────────────────────
    LOG_LEVEL: str = "DEBUG"
    LOG_PATH: str = str(BASE_DIR / "logs" / "jarvis.log")

    # ── Safety ───────────────────────────────────────────
    REQUIRE_CONFIRMATION_HIGH_RISK: bool = True


settings = Settings()
