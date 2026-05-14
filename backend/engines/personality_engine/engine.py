"""
JARVIS OS — Personality Engine (Phase 3)
Modifies the AI's system prompt dynamically based on time of day, system state, and user preferences.
"""
import datetime
from loguru import logger

from ...state import state_manager


class PersonalityEngine:
    """
    Manages JARVIS's tone, mood, and persona.
    Injects dynamic modifiers into the core System Prompt.
    """
    def __init__(self):
        self._ready = False

    def get_dynamic_prompt_modifiers(self) -> str:
        """
        Returns a string of modifiers to append to the system prompt.
        Adjusts based on time of day and current mode.
        """
        now = datetime.datetime.now()
        hour = now.hour

        modifiers = []

        # ── Time of Day Awareness ──
        if 5 <= hour < 12:
            modifiers.append("It is morning. Be crisp, energetic, and ready for the day's tasks.")
        elif 12 <= hour < 18:
            modifiers.append("It is afternoon. Be efficient and focused.")
        elif 18 <= hour < 22:
            modifiers.append("It is evening. Be relaxed but attentive.")
        else:
            modifiers.append("It is late at night. Be extremely concise, quiet, and do not be overly conversational.")

        # ── Mode Awareness ──
        mode = state_manager.mode.value
        if mode == "FOCUS":
            modifiers.append("The user is in FOCUS mode. Do NOT initiate small talk. Respond with the absolute minimum words required. Suppress non-critical warnings.")
        elif mode == "OBSERVATION":
            modifiers.append("You are in OBSERVATION mode. Just acknowledge commands quietly, do not elaborate.")

        if not modifiers:
            return ""

        return "\n[DYNAMIC PERSONALITY MODIFIERS]\n" + "\n".join(f"- {m}" for m in modifiers)

    async def start(self) -> None:
        self._ready = True
        logger.success("[Personality] Started")

    async def stop(self) -> None:
        logger.info("[Personality] Stopped")

# ── Singleton ──
personality_engine = PersonalityEngine()
